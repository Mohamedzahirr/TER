from django.core.management.base import BaseCommand
from django.core.files import File
from django.conf import settings
from accounts.models import CustomUser, Availability
from faker import Faker
import random
import string
import os
from PIL import Image

class Command(BaseCommand):
    help = 'Crée automatiquement des employés ou des chefs d\'équipe avec des informations différentes'
# Ajouter un argument
    def add_arguments(self, parser):
        parser.add_argument('count', type=int, help='Nombre d\'employés à créer')
        parser.add_argument('--manager', type=int, help='ID du manager qui crée ces employés')
        parser.add_argument('--role', type=str, choices=['employee', 'team_lead'], 
                            help='Rôle à attribuer (employee ou team_lead)')

    def generate_random_image(self):
        temp_dir = os.path.join(settings.MEDIA_ROOT, 'temp')
        os.makedirs(temp_dir, exist_ok=True)
        img = Image.new('RGB', (100, 100), color = (random.randint(0,255), random.randint(0,255), random.randint(0,255)))
        img_path = os.path.join(temp_dir, f'random_img_{random.randint(1,1000)}.png')
        img.save(img_path)
        return img_path

    def handle(self, *args, **kwargs):
        count = kwargs['count']
        manager_id = kwargs.get('manager')
        role = kwargs.get('role')
        
        if not role:
            self.stdout.write(self.style.ERROR('Veuillez spécifier un rôle (--role employee ou --role team_lead)'))
            return

        fake = Faker('fr_FR')
        days = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']

        manager = None
        if manager_id:
            try:
                manager = CustomUser.objects.get(id=manager_id)
            except CustomUser.DoesNotExist:
                self.stdout.write(self.style.ERROR(f'Manager avec ID {manager_id} non trouvé'))
                return

        for i in range(count):
            username = fake.user_name()
            email = fake.email()
            password = ''.join(random.choices(string.ascii_letters + string.digits, k=10))
            first_name = fake.first_name()
            last_name = fake.last_name()

            photo_path = self.generate_random_image()

    # Créer un nouvel utilisateur CustomUser avec les informations générées

            custom_user = CustomUser.objects.create_user(
                username=username,
                email=email,
                password=password,
                first_name=first_name,
                last_name=last_name,
                role=role,
                hours_per_week=35 if role == 'team_lead' else random.choice([20, 30, 35, 40]),
                created_by=manager
            )

            with open(photo_path, 'rb') as f:
                custom_user.photo.save(f'photo_{custom_user.id}.png', File(f), save=True)

            os.remove(photo_path)
            
    # Pour chaque jour de la semaine, déterminer aléatoirement si l'utilisateur est disponible ce jour-là

            for day in days:
                if random.choice([True, False]):
                    start_hour = random.randint(8, 12)
                    end_hour = random.randint(start_hour + 4, 20)
                    Availability.objects.create(
                        user=custom_user,
                        day_of_week=day,
                        start_time=f"{start_hour:02d}:00",
                        end_time=f"{end_hour:02d}:00"
                    )

            self.stdout.write(self.style.SUCCESS(f'{role.capitalize()} créé avec succès: {username}'))