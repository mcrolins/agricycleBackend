from django.db import migrations, models


def promote_existing_staff_to_admin(apps, schema_editor):
    User = apps.get_model("accounts", "User")
    User.objects.filter(is_superuser=True).update(role="ADMIN", is_staff=True)
    User.objects.filter(is_staff=True).exclude(role="ADMIN").update(role="ADMIN")


class Migration(migrations.Migration):
    dependencies = [
        ("accounts", "0001_initial"),
    ]

    operations = [
        migrations.AlterField(
            model_name="user",
            name="role",
            field=models.CharField(
                choices=[
                    ("ADMIN", "Admin"),
                    ("FARMER", "Farmer"),
                    ("PROCESSOR", "Processor"),
                ],
                max_length=20,
            ),
        ),
        migrations.RunPython(promote_existing_staff_to_admin, migrations.RunPython.noop),
    ]
