# Generated by Django 5.0.1 on 2024-01-31 03:18

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('supplies', '0003_alter_sitecategory_parent_category'),
    ]

    operations = [
        migrations.AlterField(
            model_name='suppliercategory',
            name='parent_category',
            field=models.ForeignKey(null=True, on_delete=django.db.models.deletion.DO_NOTHING, to='supplies.suppliercategory'),
        ),
        migrations.AlterField(
            model_name='suppliercategory',
            name='site_category',
            field=models.ForeignKey(null=True, on_delete=django.db.models.deletion.DO_NOTHING, related_name='supplier_categories', to='supplies.sitecategory'),
        ),
    ]
