# Generated by Django 2.1 on 2020-06-04 16:33

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('django_apscheduler_ng', '0001_initial'),
    ]

    operations = [
        migrations.AlterField(
            model_name='djangojob',
            name='id',
            field=models.CharField(max_length=64, primary_key=True, serialize=False),
        ),
    ]
