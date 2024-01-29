# Generated by Django 5.0.1 on 2024-01-28 11:27

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('backend', '0012_newordercodes'),
    ]

    operations = [
        migrations.AddField(
            model_name='newordercodes',
            name='order',
            field=models.ForeignKey(blank=True, default=1, on_delete=django.db.models.deletion.CASCADE, related_name='new_codes', to='backend.order'),
            preserve_default=False,
        ),
    ]
