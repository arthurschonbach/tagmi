# Generated by Django 5.2 on 2025-05-18 00:47

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0003_alter_photo_image'),
    ]

    operations = [
        migrations.AlterField(
            model_name='photo',
            name='image',
            field=models.ImageField(upload_to='photos/%Y/%m/%d/', verbose_name='image'),
        ),
    ]
