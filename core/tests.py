import tempfile
import shutil
from django.test import TestCase, Client, override_settings
from django.contrib.auth.models import User
from django.urls import reverse
from django.core.files.uploadedfile import SimpleUploadedFile
from django.conf import settings as django_settings
from django.contrib.messages import get_messages
from django import forms as django_forms # For forms.Media
from django.db import utils as django_db_utils # For IntegrityError

from .models import Group, Photo, Tag, PhotoTag
from .forms import GroupForm, PhotoTagAssignmentForm, TagFilterForm

# Helper function to create a tiny valid PNG image for uploads
def get_temporary_image(name="test_image.png"):
    return SimpleUploadedFile(
        name,
        b'\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01\x08\x06\x00\x00\x00\x1f\x15\xc4\x89\x00\x00\x00\x01sRGB\x00\xae\xce\x1c\xe9\x00\x00\x00\x0bIDAT\x08\xd7c`\x00\x00\x00\x02\x00\x01\xe2!\xbc\x33\x00\x00\x00\x00IEND\xaeB`\x82',
        'image/png'
    )

def get_another_temporary_image(name="test_image_2.png"):
    return SimpleUploadedFile(
        name,
        b'\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01\x08\x06\x00\x00\x00\x1f\x15\xc4\x89\x00\x00\x00\x01sRGB\x00\xae\xce\x1c\xe9\x00\x00\x00\x0cIDATx\x9cc\xf8\xff\xff?\x03\x00\x08\xfb\x03\xfc\x77\x01\x00\x00\x00\x00IEND\xaeB`\x82', # Different content
        'image/png'
    )

@override_settings(MEDIA_ROOT=tempfile.mkdtemp(prefix="photoshare_test_media_"))
class PhotoShareTestCase(TestCase):

    @classmethod
    def setUpTestData(cls):
        cls.user1 = User.objects.create_user(username='user1', password='password123', email='user1@example.com')
        cls.user2 = User.objects.create_user(username='user2', password='password123', email='user2@example.com')
        cls.user3 = User.objects.create_user(username='user3', password='password123', email='user3@example.com') # Not in any group initially

        cls.group1 = Group.objects.create(name='Group 1 Alpha', created_by=cls.user1)
        cls.group1.members.add(cls.user1, cls.user2)

        cls.group2 = Group.objects.create(name='Group 2 Beta', created_by=cls.user2)
        cls.group2.members.add(cls.user2)
        
        # Photos
        cls.photo1_user1 = Photo.objects.create(image=get_temporary_image("p1.png"), uploaded_by=cls.user1)
        cls.photo2_user1 = Photo.objects.create(image=get_temporary_image("p2.png"), uploaded_by=cls.user1)
        cls.photo3_user2 = Photo.objects.create(image=get_temporary_image("p3.png"), uploaded_by=cls.user2)

        # Tags
        cls.tag_g1_nature = Tag.objects.create(name="Nature", group=cls.group1)
        cls.tag_g1_city = Tag.objects.create(name="City", group=cls.group1)
        cls.tag_g2_animal = Tag.objects.create(name="Animal", group=cls.group2)
        # For testing unique_together constraint: same name in different group
        cls.tag_g2_also_nature = Tag.objects.create(name="Nature", group=cls.group2)


        # PhotoTag associations
        # Photo1 in Group1, tagged Nature
        cls.pt_g1_p1 = PhotoTag.objects.create(photo=cls.photo1_user1, group=cls.group1)
        cls.pt_g1_p1.tags.add(cls.tag_g1_nature)

        # Photo2 in Group1, tagged Nature and City
        cls.pt_g1_p2 = PhotoTag.objects.create(photo=cls.photo2_user1, group=cls.group1)
        cls.pt_g1_p2.tags.add(cls.tag_g1_nature, cls.tag_g1_city)
        
        # Photo3 in Group2, tagged Animal
        cls.pt_g2_p3 = PhotoTag.objects.create(photo=cls.photo3_user2, group=cls.group2)
        cls.pt_g2_p3.tags.add(cls.tag_g2_animal)

        # Photo1 also in Group2, no tags yet in this context
        cls.pt_g2_p1 = PhotoTag.objects.create(photo=cls.photo1_user1, group=cls.group2)


    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(django_settings.MEDIA_ROOT, ignore_errors=True)
        super().tearDownClass()

    def setUp(self):
        self.client = Client()
        self.login_url = reverse('account_login') # Assuming django-allauth

    # Model Tests
    def test_group_str(self):
        self.assertEqual(str(self.group1), 'Group 1 Alpha')

    def test_photo_str(self):
        expected_str = f"Photo by {self.user1.username} on {self.photo1_user1.uploaded_at.strftime('%Y-%m-%d')}"
        self.assertEqual(str(self.photo1_user1), expected_str)

    def test_tag_str(self):
        self.assertEqual(str(self.tag_g1_nature), "Nature")

    def test_phototag_str(self):
        expected_str = f"Photo {self.photo1_user1.id} in Group '{self.group1.name}'"
        self.assertEqual(str(self.pt_g1_p1), expected_str)

    def test_tag_unique_together_name_group(self):
        # Test that creating a tag with the same name in the same group raises IntegrityError
        with self.assertRaises(django_db_utils.IntegrityError):
            Tag.objects.create(name=self.tag_g1_nature.name, group=self.group1)
        
        # The fact that self.tag_g1_nature (name="Nature", group=self.group1) and
        # self.tag_g2_also_nature (name="Nature", group=self.group2) were successfully
        # created in setUpTestData already proves that the unique_together constraint
        # allows the same tag name in different groups.

    def test_phototag_unique_together_photo_group(self):
        with self.assertRaises(django_db_utils.IntegrityError):
            PhotoTag.objects.create(photo=self.photo1_user1, group=self.group1)
    
    def test_group_deletion_cascades_tags(self):
        group_to_delete = Group.objects.create(name="Temp Group", created_by=self.user1)
        tag_in_temp_group = Tag.objects.create(name="Temp Tag", group=group_to_delete)
        tag_id = tag_in_temp_group.id
        group_to_delete.delete()
        self.assertFalse(Tag.objects.filter(id=tag_id).exists())

    def test_photo_deletion_cascades_phototags(self):
        photo_to_delete = Photo.objects.create(image=get_temporary_image("temp_p.png"), uploaded_by=self.user1)
        pt_assoc = PhotoTag.objects.create(photo=photo_to_delete, group=self.group1)
        pt_id = pt_assoc.id
        photo_to_delete.delete()
        self.assertFalse(PhotoTag.objects.filter(id=pt_id).exists())

    def test_group_deletion_cascades_phototags(self):
        group_to_delete = Group.objects.create(name="Temp Group For PT", created_by=self.user1)
        photo_for_pt = Photo.objects.create(image=get_temporary_image("temp_p_for_pt.png"), uploaded_by=self.user1)
        pt_assoc = PhotoTag.objects.create(photo=photo_for_pt, group=group_to_delete)
        pt_id = pt_assoc.id
        group_to_delete.delete()
        self.assertFalse(PhotoTag.objects.filter(id=pt_id).exists())

    # Form Tests
    def test_group_form_valid(self):
        form_data = {'name': 'New Test Group', 'members': [self.user1.id, self.user2.id]}
        form = GroupForm(data=form_data)
        self.assertTrue(form.is_valid(), form.errors)

    def test_group_form_invalid_no_name(self):
        form_data = {'name': '', 'members': [self.user1.id]}
        form = GroupForm(data=form_data)
        self.assertFalse(form.is_valid())
        self.assertIn('name', form.errors)

    def test_group_form_invalid_no_members(self):
        # 'members' is required=True in the form
        form_data = {'name': 'Test Group No Members', 'members': []}
        form = GroupForm(data=form_data)
        self.assertFalse(form.is_valid())
        self.assertIn('members', form.errors)

    def test_phototag_assignment_form_queryset(self):
        form_g1 = PhotoTagAssignmentForm(group=self.group1)
        self.assertIn(self.tag_g1_nature, form_g1.fields['tags_to_assign'].queryset)
        self.assertIn(self.tag_g1_city, form_g1.fields['tags_to_assign'].queryset)
        self.assertNotIn(self.tag_g2_animal, form_g1.fields['tags_to_assign'].queryset)
        
        form_g2 = PhotoTagAssignmentForm(group=self.group2)
        self.assertIn(self.tag_g2_animal, form_g2.fields['tags_to_assign'].queryset)
        self.assertNotIn(self.tag_g1_nature, form_g2.fields['tags_to_assign'].queryset)

    def test_phototag_assignment_form_valid(self):
        form_data = {'tags_to_assign': [self.tag_g1_city.id]}
        form = PhotoTagAssignmentForm(data=form_data, group=self.group1)
        self.assertTrue(form.is_valid(), form.errors)

    def test_tagfilter_form_queryset(self):
        form_g1 = TagFilterForm(group=self.group1)
        self.assertIn(self.tag_g1_nature, form_g1.fields['tags_to_filter_by'].queryset)
        self.assertNotIn(self.tag_g2_animal, form_g1.fields['tags_to_filter_by'].queryset)

    # View Tests
    def test_home_view(self):
        response = self.client.get(reverse('home'))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'core/home.html')

    # GroupCreateView Tests
    def test_group_create_view_get_unauthenticated(self):
        response = self.client.get(reverse('create_group'))
        self.assertRedirects(response, f"{self.login_url}?next={reverse('create_group')}")

    def test_group_create_view_get_authenticated(self):
        self.client.login(username='user1', password='password123')
        response = self.client.get(reverse('create_group'))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'core/create_group.html')
        self.assertIsInstance(response.context['form'], GroupForm)

    def test_group_create_view_post_valid(self):
        self.client.login(username='user1', password='password123')
        initial_group_count = Group.objects.count()
        form_data = {'name': 'My New Group From Test', 'members': [self.user2.id]}
        response = self.client.post(reverse('create_group'), data=form_data, follow=True)
        
        self.assertEqual(Group.objects.count(), initial_group_count + 1)
        new_group = Group.objects.latest('id')
        self.assertEqual(new_group.name, 'My New Group From Test')
        self.assertEqual(new_group.created_by, self.user1)
        self.assertIn(self.user1, new_group.members.all()) # Creator automatically added
        self.assertIn(self.user2, new_group.members.all()) # Selected member added
        self.assertRedirects(response, reverse('group_list'))
        messages = list(get_messages(response.wsgi_request))
        self.assertEqual(len(messages), 1)
        self.assertEqual(str(messages[0]), f"Group '{new_group.name}' created successfully.")

    def test_group_create_view_post_valid_creator_already_in_members_field(self):
        self.client.login(username='user1', password='password123')
        form_data = {'name': 'Creator Included Group', 'members': [self.user1.id, self.user2.id]}
        response = self.client.post(reverse('create_group'), data=form_data)
        self.assertEqual(response.status_code, 302) # Redirect
        new_group = Group.objects.get(name='Creator Included Group')
        self.assertIn(self.user1, new_group.members.all())
        self.assertEqual(new_group.members.filter(id=self.user1.id).count(), 1) # Ensure not added twice

    def test_group_create_view_post_invalid(self):
        self.client.login(username='user1', password='password123')
        form_data = {'name': '', 'members': [self.user2.id]} # Invalid: name is empty
        response = self.client.post(reverse('create_group'), data=form_data)
        self.assertEqual(response.status_code, 200) # Re-renders form
        self.assertFormError(response.context['form'], 'name', 'This field is required.')

    # GroupListView Tests
    def test_group_list_view_unauthenticated(self):
        response = self.client.get(reverse('group_list'))
        self.assertRedirects(response, f"{self.login_url}?next={reverse('group_list')}")

    def test_group_list_view_authenticated_user1(self):
        self.client.login(username='user1', password='password123')
        response = self.client.get(reverse('group_list'))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'core/group_list.html')
        self.assertIn(self.group1, response.context['groups'])
        self.assertNotIn(self.group2, response.context['groups']) # user1 not member of group2

    def test_group_list_view_authenticated_user2(self):
        self.client.login(username='user2', password='password123')
        response = self.client.get(reverse('group_list'))
        self.assertIn(self.group1, response.context['groups'])
        self.assertIn(self.group2, response.context['groups'])

    # GroupDetailView Tests
    def test_group_detail_view_unauthenticated(self):
        response = self.client.get(reverse('group_detail', kwargs={'pk': self.group1.pk}))
        self.assertRedirects(response, f"{self.login_url}?next={reverse('group_detail', kwargs={'pk': self.group1.pk})}")

    def test_group_detail_view_authenticated_member(self):
        self.client.login(username='user1', password='password123')
        response = self.client.get(reverse('group_detail', kwargs={'pk': self.group1.pk}))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'core/group_detail.html')
        self.assertEqual(response.context['group'], self.group1)
        self.assertIsInstance(response.context['filter_form'], TagFilterForm)
        self.assertIsInstance(response.context['media'], django_forms.Media)
        
        photo_details_list = response.context['photo_details_list']
        self.assertTrue(len(photo_details_list) >= 1) 
        
        detail_item_p1 = next((item for item in photo_details_list if item['photo'] == self.photo1_user1), None)
        self.assertIsNotNone(detail_item_p1)
        self.assertEqual(detail_item_p1['photo_tag_association'], self.pt_g1_p1)
        self.assertIsInstance(detail_item_p1['tag_assignment_form'], PhotoTagAssignmentForm)
        self.assertIn(self.tag_g1_nature, detail_item_p1['current_tags_on_photo'])

    def test_group_detail_view_authenticated_non_member(self):
        self.client.login(username='user3', password='password123') 
        response = self.client.get(reverse('group_detail', kwargs={'pk': self.group1.pk}))
        self.assertEqual(response.status_code, 404)

    def test_group_detail_view_filter_by_tag(self):
        self.client.login(username='user1', password='password123')
        filter_url = reverse('group_detail', kwargs={'pk': self.group1.pk}) + f"?tags_to_filter_by={self.tag_g1_city.id}"
        response = self.client.get(filter_url)
        self.assertEqual(response.status_code, 200)
        photo_details_list = response.context['photo_details_list']
        self.assertEqual(len(photo_details_list), 1)
        self.assertEqual(photo_details_list[0]['photo'], self.photo2_user1)

        filter_url_nature = reverse('group_detail', kwargs={'pk': self.group1.pk}) + f"?tags_to_filter_by={self.tag_g1_nature.id}"
        response_nature = self.client.get(filter_url_nature)
        self.assertEqual(response_nature.status_code, 200)
        photo_details_list_nature = response_nature.context['photo_details_list']
        self.assertEqual(len(photo_details_list_nature), 2)
        photo_ids_in_list = {item['photo'].id for item in photo_details_list_nature}
        self.assertIn(self.photo1_user1.id, photo_ids_in_list)
        self.assertIn(self.photo2_user1.id, photo_ids_in_list)

    def test_group_detail_view_non_existent_group(self):
        self.client.login(username='user1', password='password123')
        response = self.client.get(reverse('group_detail', kwargs={'pk': 9999}))
        self.assertEqual(response.status_code, 404)

    # handleMultipleImagesUpload Tests
    def test_handle_multiple_images_upload_get_unauthenticated(self):
        response = self.client.get(reverse('upload_photo'))
        self.assertRedirects(response, f"{self.login_url}?next={reverse('upload_photo')}")
        
    def test_handle_multiple_images_upload_get_authenticated(self):
        self.client.login(username='user1', password='password123')
        response = self.client.get(reverse('upload_photo'))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'core/upload_photos.html')
        user_groups_in_context = response.context['groups']
        self.assertIn(self.group1, user_groups_in_context)
        self.assertNotIn(self.group2, user_groups_in_context)

    def test_handle_multiple_images_upload_post_valid(self):
        self.client.login(username='user1', password='password123')
        initial_photo_count = Photo.objects.count()
        initial_phototag_count = PhotoTag.objects.count()
        
        img1 = get_temporary_image("upload1.png")
        img2 = get_another_temporary_image("upload2.png")
        
        form_data = {'groups': [self.group1.id], 'images': [img1, img2]}
        
        response = self.client.post(reverse('upload_photo'), data=form_data, follow=True)
        self.assertRedirects(response, reverse('group_list'))
        
        self.assertEqual(Photo.objects.count(), initial_photo_count + 2)
        self.assertEqual(PhotoTag.objects.count(), initial_phototag_count + 2)

        messages = list(get_messages(response.wsgi_request))
        self.assertEqual(len(messages), 1)
        self.assertEqual(str(messages[0]), "2 photo(s) uploaded and associated with 2 group entries.")

        new_photos = Photo.objects.filter(uploaded_by=self.user1).order_by('-uploaded_at')[:2]
        for photo in new_photos:
            self.assertTrue(PhotoTag.objects.filter(photo=photo, group=self.group1).exists())

    def test_handle_multiple_images_upload_post_no_images(self):
        self.client.login(username='user1', password='password123')
        form_data = {'groups': [self.group1.id]}
        response = self.client.post(reverse('upload_photo'), data=form_data)
        self.assertEqual(response.status_code, 200)
        messages = list(get_messages(response.wsgi_request))
        self.assertEqual(len(messages), 1)
        self.assertEqual(str(messages[0]), "Please select at least one image to upload.")

    def test_handle_multiple_images_upload_post_no_groups(self):
        self.client.login(username='user1', password='password123')
        img1 = get_temporary_image(name="img_no_group.png")
        form_data = {'images': [img1]}
        response = self.client.post(reverse('upload_photo'), data=form_data)
        self.assertEqual(response.status_code, 200)
        messages = list(get_messages(response.wsgi_request))
        self.assertEqual(len(messages), 1)
        self.assertEqual(str(messages[0]), "Please select at least one group.")

    def test_handle_multiple_images_upload_post_invalid_group_id(self):
        self.client.login(username='user1', password='password123')
        img1 = get_temporary_image(name="img_invalid_group.png")
        form_data = {'images': [img1], 'groups': [self.group2.id, 999]}
        response = self.client.post(reverse('upload_photo'), data=form_data)
        self.assertEqual(response.status_code, 200)
        messages = list(get_messages(response.wsgi_request))
        self.assertEqual(len(messages), 1)
        self.assertEqual(str(messages[0]), "Invalid or no accessible groups selected.")


    # Tag Management Views
    def test_add_group_tag_view_unauthenticated(self):
        response = self.client.post(reverse('add_group_tag', kwargs={'group_pk': self.group1.pk}), {'tag_name': 'Test'})
        self.assertRedirects(response, f"{self.login_url}?next={reverse('add_group_tag', kwargs={'group_pk': self.group1.pk})}")

    def test_add_group_tag_view_success(self):
        self.client.login(username='user1', password='password123')
        response = self.client.post(reverse('add_group_tag', kwargs={'group_pk': self.group1.pk}), 
                                    {'tag_name': 'New Unique Tag'}, follow=True)
        self.assertRedirects(response, reverse('group_detail', kwargs={'pk': self.group1.pk}))
        self.assertTrue(Tag.objects.filter(group=self.group1, name='New Unique Tag').exists())
        messages = list(get_messages(response.wsgi_request))
        self.assertEqual(str(messages[0]), "Tag 'New Unique Tag' added to group 'Group 1 Alpha'.")

    def test_add_group_tag_view_existing_tag(self):
        self.client.login(username='user1', password='password123')
        response = self.client.post(reverse('add_group_tag', kwargs={'group_pk': self.group1.pk}), 
                                    {'tag_name': self.tag_g1_nature.name.upper()}, follow=True)
        self.assertRedirects(response, reverse('group_detail', kwargs={'pk': self.group1.pk}))
        messages = list(get_messages(response.wsgi_request))
        self.assertEqual(str(messages[0]), f"Tag '{self.tag_g1_nature.name}' already exists in group '{self.group1.name}'.")

    def test_add_group_tag_view_empty_name(self):
        self.client.login(username='user1', password='password123')
        response = self.client.post(reverse('add_group_tag', kwargs={'group_pk': self.group1.pk}), 
                                    {'tag_name': ' '}, follow=True)
        self.assertRedirects(response, reverse('group_detail', kwargs={'pk': self.group1.pk}))
        messages = list(get_messages(response.wsgi_request))
        self.assertEqual(str(messages[0]), "Tag name cannot be empty.")

    def test_add_group_tag_view_non_member(self):
        self.client.login(username='user3', password='password123')
        response = self.client.post(reverse('add_group_tag', kwargs={'group_pk': self.group1.pk}), {'tag_name': 'Test'})
        self.assertEqual(response.status_code, 404)

    def test_remove_group_tag_view_success(self):
        self.client.login(username='user1', password='password123')
        self.assertTrue(self.pt_g1_p1.tags.filter(id=self.tag_g1_nature.id).exists())
        tag_id_to_remove = self.tag_g1_nature.id
        tag_name_to_remove = self.tag_g1_nature.name

        response = self.client.post(reverse('remove_group_tag', kwargs={'group_pk': self.group1.pk, 'tag_pk': tag_id_to_remove}), 
                                    follow=True)
        self.assertRedirects(response, reverse('group_detail', kwargs={'pk': self.group1.pk}))
        self.assertFalse(Tag.objects.filter(id=tag_id_to_remove).exists())
        self.pt_g1_p1.refresh_from_db()
        self.assertFalse(self.pt_g1_p1.tags.filter(id=tag_id_to_remove).exists())
        messages = list(get_messages(response.wsgi_request))
        self.assertEqual(str(messages[0]), f"Tag '{tag_name_to_remove}' and its associations within this group have been removed.")

    def test_remove_group_tag_view_non_member(self):
        self.client.login(username='user3', password='password123')
        response = self.client.post(reverse('remove_group_tag', kwargs={'group_pk': self.group1.pk, 'tag_pk': self.tag_g1_nature.pk}))
        self.assertEqual(response.status_code, 404)

    # Photo Tag Assignment/Removal Views
    def test_assign_photo_tags_view_success(self):
        self.client.login(username='user1', password='password123')
        form_data = {'tags_to_assign': [self.tag_g1_nature.id, self.tag_g1_city.id]}
        response = self.client.post(reverse('assign_photo_tags', 
                                            kwargs={'group_pk': self.group1.pk, 'photo_pk': self.photo1_user1.pk}),
                                    data=form_data, follow=True)
        
        self.assertRedirects(response, reverse('group_detail', kwargs={'pk': self.group1.pk}))
        self.pt_g1_p1.refresh_from_db()
        self.assertIn(self.tag_g1_nature, self.pt_g1_p1.tags.all())
        self.assertIn(self.tag_g1_city, self.pt_g1_p1.tags.all())
        messages = list(get_messages(response.wsgi_request))
        self.assertEqual(str(messages[0]), f"Tags updated for photo in group '{self.group1.name}'.")

    def test_assign_photo_tags_view_clear_tags(self):
        self.client.login(username='user1', password='password123')
        form_data = {'tags_to_assign': []}
        self.client.post(reverse('assign_photo_tags', 
                                 kwargs={'group_pk': self.group1.pk, 'photo_pk': self.photo1_user1.pk}),
                         data=form_data)
        self.pt_g1_p1.refresh_from_db()
        self.assertEqual(self.pt_g1_p1.tags.count(), 0)


    def test_assign_photo_tags_view_invalid_form_tag_not_in_group(self):
        self.client.login(username='user1', password='password123')
        form_data = {'tags_to_assign': [self.tag_g2_animal.id]}
        response = self.client.post(reverse('assign_photo_tags',
                                            kwargs={'group_pk': self.group1.pk, 'photo_pk': self.photo1_user1.pk}),
                                    data=form_data, follow=True)
        messages = list(get_messages(response.wsgi_request))
        self.assertTrue(any("Select a valid choice" in str(m) for m in messages))
        self.pt_g1_p1.refresh_from_db()
        self.assertNotIn(self.tag_g2_animal, self.pt_g1_p1.tags.all())
        self.assertIn(self.tag_g1_nature, self.pt_g1_p1.tags.all())


    def test_assign_photo_tags_view_non_member(self):
        self.client.login(username='user3', password='password123')
        response = self.client.post(reverse('assign_photo_tags', 
                                            kwargs={'group_pk': self.group1.pk, 'photo_pk': self.photo1_user1.pk}),
                                    data={'tags_to_assign': [self.tag_g1_city.id]})
        self.assertEqual(response.status_code, 404)

    def test_remove_specific_photo_tag_view_success(self):
        self.client.login(username='user1', password='password123')
        self.assertIn(self.tag_g1_city, self.pt_g1_p2.tags.all())
        response = self.client.post(reverse('remove_specific_photo_tag', 
                                            kwargs={'group_pk': self.group1.pk, 
                                                    'phototag_pk': self.pt_g1_p2.pk, 
                                                    'tag_pk': self.tag_g1_city.pk}),
                                    follow=True)
        self.assertRedirects(response, reverse('group_detail', kwargs={'pk': self.group1.pk}))
        self.pt_g1_p2.refresh_from_db()
        self.assertNotIn(self.tag_g1_city, self.pt_g1_p2.tags.all())
        self.assertIn(self.tag_g1_nature, self.pt_g1_p2.tags.all())
        messages = list(get_messages(response.wsgi_request))
        self.assertEqual(str(messages[0]), f"Tag '{self.tag_g1_city.name}' removed from photo in group '{self.group1.name}'.")

    def test_remove_specific_photo_tag_view_tag_not_on_photo(self):
        self.client.login(username='user1', password='password123')
        response = self.client.post(reverse('remove_specific_photo_tag', 
                                            kwargs={'group_pk': self.group1.pk, 
                                                    'phototag_pk': self.pt_g1_p1.pk, 
                                                    'tag_pk': self.tag_g1_city.pk}), 
                                    follow=True)
        self.assertRedirects(response, reverse('group_detail', kwargs={'pk': self.group1.pk}))
        messages = list(get_messages(response.wsgi_request))
        self.assertEqual(str(messages[0]), f"Tag '{self.tag_g1_city.name}' was not assigned to this photo in group '{self.group1.name}'.")

    def test_remove_specific_photo_tag_view_non_member(self):
        self.client.login(username='user3', password='password123')
        response = self.client.post(reverse('remove_specific_photo_tag', 
                                            kwargs={'group_pk': self.group1.pk, 
                                                    'phototag_pk': self.pt_g1_p1.pk, 
                                                    'tag_pk': self.tag_g1_nature.pk}))
        self.assertEqual(response.status_code, 404)

    # Remove Photo From Group View
    def test_remove_photo_from_group_view_success(self):
        self.client.login(username='user1', password='password123')
        phototag_id_to_remove = self.pt_g1_p1.id
        self.assertTrue(PhotoTag.objects.filter(id=phototag_id_to_remove).exists())
        
        response = self.client.post(reverse('remove_photo_from_group', 
                                            kwargs={'group_pk': self.group1.pk, 'photo_pk': self.photo1_user1.pk}),
                                    follow=True)
        self.assertRedirects(response, reverse('group_detail', kwargs={'pk': self.group1.pk}))
        self.assertFalse(PhotoTag.objects.filter(id=phototag_id_to_remove).exists())
        messages = list(get_messages(response.wsgi_request))
        self.assertEqual(str(messages[0]), f"Photo removed from group '{self.group1.name}'.")
        
        self.assertTrue(PhotoTag.objects.filter(photo=self.photo1_user1, group=self.group2).exists())


    def test_remove_photo_from_group_view_non_member(self):
        self.client.login(username='user3', password='password123')
        response = self.client.post(reverse('remove_photo_from_group', 
                                            kwargs={'group_pk': self.group1.pk, 'photo_pk': self.photo1_user1.pk}))
        self.assertEqual(response.status_code, 404)

    def test_remove_photo_from_group_view_photo_not_in_group(self):
        self.client.login(username='user1', password='password123')
        response = self.client.post(reverse('remove_photo_from_group', 
                                            kwargs={'group_pk': self.group1.pk, 'photo_pk': self.photo3_user2.pk}),
                                    follow=True)
        self.assertFalse(PhotoTag.objects.filter(photo=self.photo3_user2, group=self.group1).exists())
        messages = list(get_messages(response.wsgi_request))
        self.assertEqual(str(messages[0]), f"Photo removed from group '{self.group1.name}'.")