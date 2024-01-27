# Generated by Django 5.0.1 on 2024-01-15 20:26

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('backend', '0002_remove_productinfo_unique_product_info_and_more'),
    ]

    operations = [
        migrations.RemoveConstraint(
            model_name='productparameter',
            name='unique_product_parameter',
        ),
        migrations.RemoveField(
            model_name='productparameter',
            name='product_info',
        ),
        migrations.AddField(
            model_name='productparameter',
            name='product',
            field=models.ForeignKey(blank=True, default=1, on_delete=django.db.models.deletion.CASCADE, related_name='product_parameters', to='backend.product', verbose_name='Продукт'),
            preserve_default=False,
        ),
        migrations.AddConstraint(
            model_name='productparameter',
            constraint=models.UniqueConstraint(fields=('product', 'parameter'), name='unique_product_parameter'),
        ),
    ]
