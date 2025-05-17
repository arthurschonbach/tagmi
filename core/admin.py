from django.contrib import admin
from django.urls import reverse
from django.utils.html import format_html
from .models import Group, Photo, Tag, PhotoTag

class MemberInline(admin.TabularInline):
    model = Group.members.through
    extra = 1
    verbose_name = "Member"
    verbose_name_plural = "Members"
    raw_id_fields = ('user',) # Better for large number of users

class PhotoTagAssociationInline(admin.TabularInline):
    """
    Inline for PhotoTag model when editing a Group or Photo.
    Allows associating photos with the current group and tagging them.
    """
    model = PhotoTag
    extra = 1
    verbose_name = "Photo Association & Tags"
    verbose_name_plural = "Photo Associations & Tags"
    fields = ('photo', 'tags') # Group is implied by the parent admin (GroupAdmin)
    raw_id_fields = ('photo',)
    filter_horizontal = ('tags',) # Better UX for ManyToMany

    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        # Limit 'group' choice in PhotoTagInline if it were ever used outside GroupAdmin.
        # For now, not strictly necessary if only used in GroupAdmin.
        # if db_field.name == "group":
        #     # Get the parent Group object's ID if available (e.g., when editing an existing Group)
        #     # This part is tricky and might need a custom InlineFormSet.
        #     # For simplicity, if this inline is only on GroupAdmin, 'group' field can be excluded or readonly.
        #     pass
        return super().formfield_for_foreignkey(db_field, request, **kwargs)

    def formfield_for_manytomany(self, db_field, request, **kwargs):
        # Limit tags to those belonging to the parent group
        if db_field.name == "tags":
            # This requires getting the parent object, which is not straightforward in Inline.
            # A custom formset is often needed for this level of dynamic filtering.
            # For now, it will show all tags. A custom formset would be a further enhancement.
            # object_id = request.resolver_match.kwargs.get('object_id')
            # if object_id:
            #     group = Group.objects.get(pk=object_id)
            #     kwargs["queryset"] = Tag.objects.filter(group=group)
            pass # Keeping it simple for now, shows all tags.
        return super().formfield_for_manytomany(db_field, request, **kwargs)


@admin.register(Group)
class GroupAdmin(admin.ModelAdmin):
    list_display = ('name', 'created_by', 'member_count')
    search_fields = ('name', 'created_by__username', 'members__username')
    inlines = [MemberInline, PhotoTagAssociationInline]
    raw_id_fields = ('created_by',)
    list_filter = ('created_by',)

    def member_count(self, obj):
        return obj.members.count()
    member_count.short_description = "Members"

    def get_queryset(self, request):
        return super().get_queryset(request).prefetch_related('members')


@admin.register(Photo)
class PhotoAdmin(admin.ModelAdmin):
    list_display = ('image_thumbnail', 'uploaded_by', 'uploaded_at', 'group_associations_list')
    search_fields = ('uploaded_by__username',)
    list_filter = ('uploaded_at', 'uploaded_by')
    raw_id_fields = ('uploaded_by',)
    readonly_fields = ('image_display',)

    def image_thumbnail(self, obj):
        if obj.image:
            return format_html('<img src="{}" style="max-height: 50px; max-width: 50px;" />', obj.image.url)
        return "No image"
    image_thumbnail.short_description = 'Thumbnail'

    def image_display(self, obj):
        if obj.image:
            return format_html('<img src="{}" style="max-height: 200px; max-width: 200px;" />', obj.image.url)
        return "No image"
    image_display.short_description = 'Image Preview'

    def group_associations_list(self, obj):
        associations = obj.group_tag_associations.all()
        if not associations:
            return "-"
        return ", ".join([f"{assoc.group.name} ({assoc.tags.count()} tags)" for assoc in associations])
    group_associations_list.short_description = "Group Associations"

    def get_queryset(self, request):
        return super().get_queryset(request).prefetch_related('group_tag_associations__group', 'group_tag_associations__tags')


@admin.register(Tag)
class TagAdmin(admin.ModelAdmin):
    list_display = ('name', 'group_link')
    search_fields = ('name', 'group__name')
    list_select_related = ('group',) # Performance optimization
    list_filter = ('group',)

    def group_link(self, obj):
        if obj.group:
            link = reverse("admin:core_group_change", args=[obj.group.id])
            return format_html('<a href="{}">{}</a>', link, obj.group.name)
        return "-"
    group_link.short_description = 'Group'
    group_link.admin_order_field = 'group__name'


@admin.register(PhotoTag)
class PhotoTagAdmin(admin.ModelAdmin):
    list_display = ('photo_thumbnail', 'group_name', 'tag_list')
    raw_id_fields = ('photo', 'group')
    filter_horizontal = ('tags',)
    list_filter = ('group', 'tags')
    search_fields = ('photo__id', 'group__name', 'tags__name')

    def photo_thumbnail(self, obj):
        if obj.photo and obj.photo.image:
            return format_html('<img src="{}" style="max-height: 50px; max-width: 50px;" />', obj.photo.image.url)
        return "No image"
    photo_thumbnail.short_description = 'Photo'

    def group_name(self, obj):
        return obj.group.name
    group_name.short_description = 'Group'
    group_name.admin_order_field = 'group__name'

    def tag_list(self, obj):
        return ", ".join([tag.name for tag in obj.tags.all()])
    tag_list.short_description = 'Tags'

    def get_queryset(self, request):
        return super().get_queryset(request).select_related('photo', 'group').prefetch_related('tags')

    def formfield_for_manytomany(self, db_field, request, **kwargs):
        # Limit tags to those belonging to the selected group for this PhotoTag instance
        if db_field.name == "tags":
            # Get the PhotoTag instance being edited, if it exists
            object_id = request.resolver_match.kwargs.get('object_id')
            if object_id:
                phototag_instance = self.get_object(request, object_id)
                if phototag_instance and phototag_instance.group:
                    kwargs["queryset"] = Tag.objects.filter(group=phototag_instance.group)
            else: # For new PhotoTag instances, this won't filter initially until group is selected.
                  # This might require JavaScript or a custom form for dynamic filtering on add page.
                kwargs["queryset"] = Tag.objects.none() # Or Tag.objects.all() as a fallback
        return super().formfield_for_manytomany(db_field, request, **kwargs)