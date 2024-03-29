# Generated by Django 5.0.1 on 2024-01-27 16:33

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('backend', '0009_alter_orderitem_product_info'),
    ]

    operations = [
        migrations.AddField(
            model_name='order',
            name='shop',
            field=models.ForeignKey(default=1, on_delete=django.db.models.deletion.CASCADE, related_name='orders', to='backend.shop'),
            preserve_default=False,
        ),
    ]
