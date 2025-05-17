from django.contrib.auth.models import User
from django.db import models
from django.utils.translation import gettext_lazy as _

class Group(models.Model):
    name = models.CharField(_("group name"), max_length=255)
    members = models.ManyToManyField(
        User,
        verbose_name=_("members"),
        related_name="photo_groups"
    )
    created_by = models.ForeignKey(
        User,
        verbose_name=_("creator"),
        on_delete=models.SET_NULL, # Or models.CASCADE if group should be deleted with creator
        null=True,
        related_name="created_photo_groups"
    )

    def __str__(self):
        return self.name

    class Meta:
        verbose_name = _("group")
        verbose_name_plural = _("groups")

class Photo(models.Model):
    image = models.ImageField(_("image"), upload_to="photos/%Y/%m/%d/")
    uploaded_by = models.ForeignKey(
        User,
        verbose_name=_("uploader"),
        on_delete=models.CASCADE,
        related_name="uploaded_photos"
    )
    uploaded_at = models.DateTimeField(_("upload time"), auto_now_add=True)

    def __str__(self):
        return f"Photo by {self.uploaded_by.username} on {self.uploaded_at.strftime('%Y-%m-%d')}"

    class Meta:
        verbose_name = _("photo")
        verbose_name_plural = _("photos")
        ordering = ['-uploaded_at']

class Tag(models.Model):
    name = models.CharField(_("tag name"), max_length=50)
    group = models.ForeignKey(
        Group,
        verbose_name=_("group"),
        on_delete=models.CASCADE,
        related_name='tags'
    )

    class Meta:
        unique_together = ('name', 'group') # Ensures tag names are unique within a group
        verbose_name = _("tag")
        verbose_name_plural = _("tags")
        ordering = ['name']

    def __str__(self):
        return self.name

class PhotoTag(models.Model):
    """
    Links a Photo to a Group and assigns specific Tags to that photo
    within the context of that Group.
    """
    photo = models.ForeignKey(
        Photo,
        verbose_name=_("photo"),
        on_delete=models.CASCADE,
        related_name='group_tag_associations' # Photo.group_tag_associations.all()
    )
    group = models.ForeignKey(
        Group,
        verbose_name=_("group"),
        on_delete=models.CASCADE,
        related_name='photo_tag_associations' # Group.photo_tag_associations.all()
    )
    tags = models.ManyToManyField(
        Tag,
        verbose_name=_("tags"),
        blank=True # A photo can be in a group without specific tags initially
    )

    class Meta:
        unique_together = ('photo', 'group') # A photo can only be associated with a group once
        verbose_name = _("photo-group tag assignment")
        verbose_name_plural = _("photo-group tag assignments")

    def __str__(self):
        return f"Photo {self.photo.id} in Group '{self.group.name}'"