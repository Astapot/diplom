# Generated by Django 5.0.1 on 2024-01-15 20:18

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('backend', '0001_initial'),
    ]

    operations = [
        migrations.RemoveConstraint(
            model_name='productinfo',
            name='unique_product_info',
        ),
        migrations.AddField(
            model_name='productinfo',
            name='external_id',
            field=models.PositiveIntegerField(blank=True, default=1, verbose_name='Внешний ИД'),
            preserve_default=False,
        ),
        migrations.AlterField(
            model_name='productinfo',
            name='model',
            field=models.CharField(blank=True, max_length=80, null=True, verbose_name='Модель'),
        ),
        migrations.AddConstraint(
            model_name='productinfo',
            constraint=models.UniqueConstraint(fields=('product', 'shop', 'external_id'), name='unique_product_info'),
        ),
    ]
