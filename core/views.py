from django.shortcuts import render, redirect, get_object_or_404
from django.urls import reverse_lazy, reverse
from django.views.generic import CreateView, ListView, DetailView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_POST
from django.contrib import messages
from django import forms as django_forms # For forms.Media

from .models import Group, Photo, Tag, PhotoTag
# MultiplePhotoUploadForm is removed from imports
from .forms import GroupForm, PhotoTagAssignmentForm, TagFilterForm

def home(request):
    return render(request, 'core/home.html')

class GroupCreateView(LoginRequiredMixin, CreateView):
    model = Group
    form_class = GroupForm
    template_name = 'core/create_group.html'

    def get_success_url(self):
        return reverse_lazy('group_list') # Return URL string for redirect after creation

    def form_valid(self, form):
        form.instance.created_by = self.request.user
        response = super().form_valid(form) # Saves the group and m2m members
        if self.request.user not in self.object.members.all():
            self.object.members.add(self.request.user)
        messages.success(self.request, f"Group '{self.object.name}' created successfully.")
        return response

class GroupListView(LoginRequiredMixin, ListView):
    model = Group
    template_name = 'core/group_list.html'
    context_object_name = 'groups'

    def get_queryset(self):
        return Group.objects.filter(members=self.request.user)\
            .select_related('created_by')\
            .prefetch_related('members')\
            .order_by('-id')

class GroupDetailView(LoginRequiredMixin, DetailView):
    model = Group
    template_name = 'core/group_detail.html'
    context_object_name = 'group'

    def get_queryset(self):
        return super().get_queryset().filter(members=self.request.user).prefetch_related(
            'members',
            'tags',
            'photo_tag_associations__photo__uploaded_by',
            'photo_tag_associations__tags'
        )

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        group = self.object

        # Formulaire de filtrage
        filter_form = TagFilterForm(self.request.GET or None, group=group)
        context['filter_form'] = filter_form

        # Associations photo <-> tags
        phototag_associations = group.photo_tag_associations.all()

        if filter_form.is_valid():
            selected_filter_tags = filter_form.cleaned_data.get('tags_to_filter_by')
            if selected_filter_tags:
                for tag in selected_filter_tags:
                    phototag_associations = phototag_associations.filter(tags=tag)
                phototag_associations = phototag_associations.distinct()

        # Construction des formulaires individuels par photo
        photo_details_list = []
        media_collector = django_forms.Media()

        for pt_assoc in phototag_associations:
            selected_tags = pt_assoc.tags.all()

            tag_assignment_form = PhotoTagAssignmentForm(
                group=group,
                selected_tags=selected_tags,
                initial={'tags_to_assign': selected_tags}
            )

            media_collector += tag_assignment_form.media

            photo_details_list.append({
                'photo_tag_association': pt_assoc,
                'photo': pt_assoc.photo,
                'current_tags_on_photo': selected_tags,
                'tag_assignment_form': tag_assignment_form
            })

        context['photo_details_list'] = photo_details_list
        context['media'] = media_collector
        return context


# Reverted to your original handleMultipleImagesUpload, with improvements
@login_required
def handleMultipleImagesUpload(request): # Ensure this matches your URL conf name
    user_groups = Group.objects.filter(members=request.user).order_by('name')

    if request.method == "POST":
        images = request.FILES.getlist('images')
        group_ids = request.POST.getlist('groups')

        if not images:
            messages.error(request, "Please select at least one image to upload.")
            return render(request, "core/upload_photos.html", {'groups': user_groups})

        if not group_ids:
            messages.error(request, "Please select at least one group.")
            return render(request, "core/upload_photos.html", {'groups': user_groups})

        # Filter selected groups to ensure user is a member (security measure)
        # and that the groups actually exist.
        selected_groups = Group.objects.filter(id__in=group_ids, members=request.user)

        if not selected_groups.exists():
            messages.error(request, "Invalid or no accessible groups selected.")
            return render(request, "core/upload_photos.html", {'groups': user_groups})
        
        photos_created_count = 0
        phototags_created_count = 0

        for image_file in images:
            # Create one Photo object per uploaded image file
            photo_instance = Photo.objects.create(image=image_file, uploaded_by=request.user)
            photos_created_count += 1
            # Associate this new photo with each selected group
            for group_instance in selected_groups:
                PhotoTag.objects.create(photo=photo_instance, group=group_instance)
                phototags_created_count += 1
        
        messages.success(request, f"{photos_created_count} photo(s) uploaded and associated with {phototags_created_count} group entries.")
        return redirect('group_list') # Or a more relevant success page, e.g., last group detail

    # GET request
    return render(request, "core/upload_photos.html", {'groups': user_groups})


@login_required
@require_POST
def add_group_tag_view(request, group_pk):
    group = get_object_or_404(Group, pk=group_pk, members=request.user)
    tag_name = request.POST.get('tag_name', '').strip()

    if not tag_name:
        messages.error(request, "Tag name cannot be empty.")
    else:
        tag, created = Tag.objects.get_or_create(
            name__iexact=tag_name,
            group=group,
            defaults={'name': tag_name}
        )
        if created:
            messages.success(request, f"Tag '{tag.name}' added to group '{group.name}'.")
        else:
            messages.info(request, f"Tag '{tag.name}' already exists in group '{group.name}'.")
    return redirect('group_detail', pk=group_pk)

@login_required
@require_POST
def remove_group_tag_view(request, group_pk, tag_pk):
    group = get_object_or_404(Group, pk=group_pk, members=request.user)
    tag = get_object_or_404(Tag, pk=tag_pk, group=group)
    
    tag_name = tag.name
    tag.delete()
    messages.success(request, f"Tag '{tag_name}' and its associations within this group have been removed.")
    return redirect('group_detail', pk=group_pk)

@login_required
@require_POST
def assign_photo_tags_view(request, group_pk, photo_pk):
    group = get_object_or_404(Group, pk=group_pk, members=request.user)
    photo = get_object_or_404(Photo, pk=photo_pk)
    
    photo_tag_association, _ = PhotoTag.objects.get_or_create(photo=photo, group=group)
    
    form = PhotoTagAssignmentForm(request.POST, group=group) # This form is still used on group_detail
    if form.is_valid():
        selected_tags = form.cleaned_data['tags_to_assign']
        photo_tag_association.tags.set(selected_tags)
        messages.success(request, f"Tags updated for photo in group '{group.name}'.")
    else:
        for field, errors in form.errors.items():
            for error in errors:
                messages.error(request, f"Error assigning tags: {field} - {error}")
    return redirect('group_detail', pk=group_pk)

@login_required
@require_POST
def remove_photo_from_group_view(request, group_pk, photo_pk):
    group = get_object_or_404(Group, pk=group_pk, members=request.user)
    photo = get_object_or_404(Photo, pk=photo_pk)
    
    # Remove the PhotoTag association for this photo in the group
    PhotoTag.objects.filter(photo=photo, group=group).delete()
    
    messages.success(request, f"Photo removed from group '{group.name}'.")
    return redirect('group_detail', pk=group_pk)