from django import forms
from django.contrib.auth.models import User
from django.utils.translation import gettext_lazy as _
from .models import Group, Tag # PhotoTag model not directly used in forms here

class GroupForm(forms.ModelForm):
    members = forms.ModelMultipleChoiceField(
        queryset=User.objects.all(),
        widget=forms.CheckboxSelectMultiple,
        required=True,
        label=_("Select members for this group"),
    )

    class Meta:
        model = Group
        fields = ['name', 'members']

# MultiplePhotoUploadForm has been removed

class PhotoTagAssignmentForm(forms.Form):
    tags_to_assign = forms.ModelMultipleChoiceField(
        queryset=Tag.objects.none(),
        widget=forms.CheckboxSelectMultiple,
        label=_("Select tags for this photo"),
        required=False
    )

    def __init__(self, *args, group=None, **kwargs):
        super().__init__(*args, **kwargs)
        if group:
            self.fields['tags_to_assign'].queryset = Tag.objects.filter(group=group).order_by('name')

class TagFilterForm(forms.Form):
    tags_to_filter_by = forms.ModelMultipleChoiceField(
        queryset=Tag.objects.none(),
        widget=forms.CheckboxSelectMultiple,
        required=False,
        label=_("Filter by tags"),
    )

    def __init__(self, *args, group=None, **kwargs):
        super().__init__(*args, **kwargs)
        if group:
            self.fields['tags_to_filter_by'].queryset = Tag.objects.filter(group=group).order_by('name')