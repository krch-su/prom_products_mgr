# Generated by Django 5.0.1 on 2024-01-31 01:43

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
    ]

    operations = [
        migrations.CreateModel(
            name='Supplier',
            fields=[
                ('_id', models.BigAutoField(primary_key=True, serialize=False)),
                ('name', models.CharField(max_length=255)),
                ('feed_url', models.URLField(max_length=1000)),
                ('active', models.BooleanField(default=False)),
            ],
        ),
        migrations.CreateModel(
            name='SiteCategory',
            fields=[
                ('id', models.BigIntegerField(primary_key=True, serialize=False)),
                ('name', models.CharField(max_length=512)),
                ('parent_category', models.ForeignKey(null=True, on_delete=django.db.models.deletion.DO_NOTHING, to='supplies.sitecategory')),
            ],
            options={
                'verbose_name': 'Site Category',
                'verbose_name_plural': 'Site Categories',
            },
        ),
        migrations.CreateModel(
            name='SupplierCategory',
            fields=[
                ('id', models.BigIntegerField(primary_key=True, serialize=False)),
                ('name', models.CharField(max_length=512)),
                ('parent_category', models.ForeignKey(null=True, on_delete=django.db.models.deletion.DO_NOTHING, to='supplies.suppliercategory')),
                ('site_category', models.ForeignKey(null=True, on_delete=django.db.models.deletion.DO_NOTHING, to='supplies.sitecategory')),
                ('supplier', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='supplies.supplier')),
            ],
            options={
                'verbose_name': 'Supplier Category',
                'verbose_name_plural': 'Supplier Categories',
            },
        ),
        migrations.CreateModel(
            name='SupplierOffer',
            fields=[
                ('_id', models.BigAutoField(primary_key=True, serialize=False)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('id', models.CharField(max_length=255)),
                ('available', models.BooleanField(default=False)),
                ('group_id', models.BigIntegerField(null=True)),
                ('url', models.URLField(null=True)),
                ('optPrice', models.DecimalField(blank=True, decimal_places=2, max_digits=10, null=True)),
                ('oldprice', models.DecimalField(blank=True, decimal_places=2, max_digits=10, null=True)),
                ('price_old', models.DecimalField(blank=True, decimal_places=2, max_digits=10, null=True)),
                ('old_price', models.DecimalField(blank=True, decimal_places=2, max_digits=10, null=True)),
                ('discount', models.DecimalField(blank=True, decimal_places=2, max_digits=10, null=True)),
                ('minimum_order_quantity', models.IntegerField(null=True)),
                ('price', models.DecimalField(decimal_places=2, max_digits=10)),
                ('currencyId', models.CharField(max_length=3)),
                ('categoryId', models.CharField(max_length=20)),
                ('pickup', models.BooleanField(null=True)),
                ('delivery', models.BooleanField(null=True)),
                ('name', models.CharField(max_length=255)),
                ('name_ua', models.CharField(max_length=255)),
                ('vendorCode', models.CharField(max_length=25)),
                ('barcode', models.CharField(max_length=25)),
                ('article', models.CharField(max_length=25)),
                ('vendor', models.CharField(max_length=64, null=True)),
                ('model', models.CharField(max_length=255, null=True)),
                ('country_of_origin', models.CharField(max_length=50, null=True)),
                ('country', models.CharField(max_length=50, null=True)),
                ('description', models.TextField()),
                ('description_ua', models.TextField()),
                ('quantity_in_stock', models.PositiveIntegerField(null=True)),
                ('stock_quantity', models.PositiveIntegerField(null=True)),
                ('keywords', models.JSONField(null=True)),
                ('keywords_ua', models.JSONField(null=True)),
                ('params', models.TextField(null=True)),
                ('pictures', models.JSONField()),
                ('gtin', models.CharField(max_length=64, null=True)),
                ('mpn', models.CharField(max_length=64, null=True)),
                ('supplier', models.ForeignKey(on_delete=django.db.models.deletion.DO_NOTHING, to='supplies.supplier')),
            ],
            options={
                'verbose_name': 'Supplier Offer',
                'verbose_name_plural': 'Supplier Offers',
            },
        ),
        migrations.CreateModel(
            name='Offer',
            fields=[
                ('_id', models.BigAutoField(primary_key=True, serialize=False)),
                ('active', models.BooleanField(default=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('group_id', models.BigIntegerField(null=True)),
                ('url', models.URLField(null=True)),
                ('name', models.CharField(max_length=255, null=True)),
                ('name_ua', models.CharField(max_length=255, null=True)),
                ('description', models.TextField(null=True)),
                ('description_ua', models.TextField(null=True)),
                ('keywords', models.JSONField(null=True)),
                ('keywords_ua', models.JSONField(null=True)),
                ('params', models.TextField(null=True)),
                ('pictures', models.JSONField(null=True)),
                ('supplier_offer', models.OneToOneField(on_delete=django.db.models.deletion.DO_NOTHING, related_name='offer', to='supplies.supplieroffer')),
            ],
            options={
                'verbose_name': 'Offer',
                'verbose_name_plural': 'Offers',
            },
        ),
    ]
