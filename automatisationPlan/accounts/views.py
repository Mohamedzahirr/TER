from email.utils import parsedate
from http.client import HTTPResponse
from io import BytesIO
import logging
from sqlite3 import OperationalError
from venv import logger
from django.contrib.auth import get_user_model, authenticate, login, logout
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.models import Group
from django.views.generic import CreateView, ListView, UpdateView, DeleteView
from django.urls import reverse_lazy, reverse
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.http import HttpResponseForbidden, HttpResponseRedirect
from rest_framework.permissions import AllowAny
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from .forms import LeaveRequestForm, SignUpForm, ManagerCreateUserForm, EmployeeEditForm, TeamLeadEditForm, AvailabilityForm,ShiftFormSet ,  ServiceConstraintsForm , ShiftRequirementForm ,EmployeeRequirementForm, UpdateLeaveRequestForm

from .models import LeaveRequest, Notification, Schedule, ScheduleEntry, CustomUser, Availability, Schedule ,ServiceConstraints , EmployeeRequirement, ShiftRequirement  , Shift, TimeClock
from .serializers import User, UserRegistrationSerializer
from django.contrib.auth.decorators import login_required
from django.shortcuts import render
from django.views import View
from django.contrib.auth import get_user_model
from .forms import ServiceConstraintsForm, ShiftRequirementFormSet , WeekSelectionForm
from django.contrib import messages
from .forms import WeekSelectionForm 
from django.http import JsonResponse
from django.template.loader import get_template  
from .forms import UserProfileForm  
from django.contrib.auth import update_session_auth_hash
from django.contrib.auth.forms import PasswordChangeForm

import pytz  

from accounts.scheduler.generate_schedule import generate_schedule



CustomUser = get_user_model()

class SignUpView(CreateView):
    form_class = SignUpForm
    template_name = 'accounts/signup.html'
    success_url = reverse_lazy('login')

    def form_valid(self, form):
        user = form.save()
        return super().form_valid(form)

class LoginView(View):
    template_name = 'accounts/login.html'

    def get(self, request):
        return render(request, self.template_name)

    def post(self, request):
        username = request.POST.get('username')
        password = request.POST.get('password')

        if not User.objects.filter(username=username).exists():
            messages.error(request, "Ce nom d'utilisateur n'existe pas.")
            return render(request, self.template_name)

        user = authenticate(request, username=username, password=password)
        if user is not None:
            login(request, user)
            return redirect('home')  # Assurez-vous que 'home' est le nom correct de votre URL de page d'accueil
        else:
            messages.error(request, "Mot de passe incorrect.")
            return render(request, self.template_name)

@login_required
def home(request):
    user = request.user
    availabilities = Availability.objects.filter(user=user)
    notification_count = Notification.objects.filter(user=user, is_read=False).count()

    # Get the first 6 employees created by the manager
    employees = CustomUser.objects.filter(created_by=user, role='employee')[:6]
    # Get the first 6 team leads created by the manager
    team_leads = CustomUser.objects.filter(created_by=user, role='team_lead')[:6]

    # Get current week schedule for the user
    start_date, end_date = get_current_week_dates()
    current_week_schedule = {}
    total_hours = 0

    if user.role != 'manager':
        schedule = Schedule.objects.filter(
            user=user.created_by,
            start_date=start_date,
            end_date=end_date
        ).first()

        if schedule:
            entries = ScheduleEntry.objects.filter(
                schedule=schedule,
                employee=user
            ).order_by('day', 'start_time')

            days = ["Lundi", "Mardi", "Mercredi", "Jeudi", "Vendredi", "Samedi", "Dimanche"]
            day_mapping = dict(zip(range(7), days))

            for entry in entries:
                day = day_mapping[entry.date.weekday()]
                if day not in current_week_schedule:
                    current_week_schedule[day] = []
                
                current_week_schedule[day].append({
                    'start_time': entry.start_time.strftime('%H:%M'),
                    'end_time': entry.end_time.strftime('%H:%M'),
                    'hours': entry.hours
                })

            total_hours = entries.aggregate(Sum('hours'))['hours__sum'] or 0

    context = {
        'user': user,
        'availabilities': availabilities,
        'notification_count': notification_count,
        'employees': employees,
        'team_leads': team_leads,
        'current_week_schedule': current_week_schedule,
        'total_hours': total_hours,
        'days': ["Lundi", "Mardi", "Mercredi", "Jeudi", "Vendredi", "Samedi", "Dimanche"],
        'start_date': start_date,
        'end_date': end_date,
    }

    return render(request, 'accounts/home.html', context)

    

@login_required
def profile_view(request):
    user = request.user
    if request.method == 'POST':
        if 'update_profile' in request.POST:
            profile_form = UserProfileForm(request.POST, request.FILES, instance=user)
            if profile_form.is_valid():
                profile_form.save()
                messages.success(request, 'Votre profil a été mis à jour avec succès.')
                return redirect('profile')
        elif 'change_password' in request.POST:
            password_form = PasswordChangeForm(user, request.POST)
            if password_form.is_valid():
                user = password_form.save()
                update_session_auth_hash(request, user)  # Important pour garder l'utilisateur connecté
                messages.success(request, 'Votre mot de passe a été changé avec succès.')
                return redirect('profile')
    else:
        profile_form = UserProfileForm(instance=user)
        password_form = PasswordChangeForm(user)

    context = {
        'user': user,
        'pointage_code': user.pointage_code,
        'profile_form': profile_form,
        'password_form': password_form,
    }
    return render(request, 'accounts/profile.html', context)

def login_view(request):
    if request.method == "POST":
        username = request.POST.get('username')
        password = request.POST.get('password')
        user = authenticate(request, username=username, password=password)
        if user is not None:
            login(request, user)
            return redirect('home')
        else:
            return render(request, 'login.html', {'error': 'Invalid credentials'})
    return render(request, 'login.html')

class ManagerCreateUserView(LoginRequiredMixin, CreateView):
    form_class = ManagerCreateUserForm
    template_name = 'accounts/create_user.html'
    success_url = reverse_lazy('home')

    def form_valid(self, form):
        user = form.save(commit=False)
        user.created_by = self.request.user
        user.is_active = True
        user.save()
        role = form.cleaned_data['role']
        if role == 'employee':
            group = Group.objects.get(name='Employee')
        elif role == 'team_lead':
            group = Group.objects.get(name='TeamLead')
        user.groups.add(group)
        return super().form_valid(form)

class EmployeeListView(LoginRequiredMixin, ListView):
    model = CustomUser
    template_name = 'accounts/employee_list.html'
    context_object_name = 'employees'

    def get_queryset(self):
        user = self.request.user
        return CustomUser.objects.filter(created_by=user, role='employee')

class TeamLeadListView(LoginRequiredMixin, ListView):
    model = CustomUser
    template_name = 'accounts/team_lead_list.html'
    context_object_name = 'team_leads'

    def get_queryset(self):
        user = self.request.user
        return CustomUser.objects.filter(created_by=user, role='team_lead')


class EmployeeUpdateView(LoginRequiredMixin, UserPassesTestMixin, UpdateView):
    model = CustomUser
    form_class = EmployeeEditForm
    template_name = 'accounts/edit_employee.html'

    def test_func(self):
        return self.request.user.is_authenticated and self.request.user.role == 'manager'

    def handle_no_permission(self):
        return HttpResponseForbidden("Vous n'avez pas la permission de modifier cet utilisateur.")

    def get_success_url(self):
        return reverse('employee_list')

    def form_valid(self, form):
        if 'photo' in self.request.FILES:
            form.instance.photo = self.request.FILES['photo']
        return super().form_valid(form)

class TeamLeadUpdateView(LoginRequiredMixin, UserPassesTestMixin, UpdateView):
    model = CustomUser
    form_class = TeamLeadEditForm
    template_name = 'accounts/edit_team_lead.html'

    def test_func(self):
        return self.request.user.is_authenticated and self.request.user.role == 'manager'

    def handle_no_permission(self):
        return HttpResponseForbidden("Vous n'avez pas la permission de modifier cet utilisateur.")

    def get_success_url(self):
        return reverse('team_lead_list')
    
    def form_valid(self, form):
        if 'photo' in self.request.FILES:
            form.instance.photo = self.request.FILES['photo']
        return super().form_valid(form)

class AvailabilityCreateView(LoginRequiredMixin, CreateView):
    model = Availability
    template_name = 'accounts/add_availability.html'
    fields = []

    def form_valid(self, form):
        user = get_object_or_404(CustomUser, pk=self.kwargs['pk'])

        days = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
        for day in days:
            not_available = self.request.POST.get(f'{day}_not_available')
            all_day = self.request.POST.get(f'{day}_all_day')
            start_time = self.request.POST.get(f'{day}_start_time')
            end_time = self.request.POST.get(f'{day}_end_time')

            if not not_available:
                if all_day:
                    start_time = '00:00'
                    end_time = '23:59'

                if start_time and end_time:
                    Availability.objects.create(
                        user=user,
                        day_of_week=day,
                        start_time=start_time,
                        end_time=end_time
                    )

        return redirect('view_availabilities', user.pk)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['user'] = get_object_or_404(CustomUser, pk=self.kwargs['pk'])
        context['days'] = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
        return context

from django.utils.timezone import datetime

class AvailabilityUpdateView(LoginRequiredMixin, UpdateView):
    model = Availability
    fields = ['day_of_week', 'start_time', 'end_time']
    template_name = 'accounts/edit_availability.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['availability'] = self.object
        return context

    def form_valid(self, form):
        not_available = self.request.POST.get('not_available') == 'on'
        all_day = self.request.POST.get('all_day') == 'on'
        start_time = self.request.POST.get('start_time')
        end_time = self.request.POST.get('end_time')

        if not_available:
            # Si l'utilisateur n'est pas disponible, on supprime l'enregistrement
            self.object.delete()
            messages.success(self.request, f"La disponibilité pour {self.object.day_of_week} a été supprimée.")
            return redirect('view_availabilities', pk=self.object.user.pk)
        elif all_day:
            # Si disponible toute la journée, on met les horaires de 00:00 à 23:59
            form.instance.start_time = datetime.min.time()
            form.instance.end_time = datetime.max.time()
        else:
            # Sinon, on utilise les horaires fournis
            if not start_time or not end_time:
                messages.error(self.request, "Les heures de début et de fin sont requises si l'utilisateur est disponible.")
                return self.form_invalid(form)
            form.instance.start_time = start_time
            form.instance.end_time = end_time

        messages.success(self.request, f"La disponibilité pour {form.instance.day_of_week} a été mise à jour avec succès.")
        return super().form_valid(form)

    def get_success_url(self):
        return reverse('view_availabilities', kwargs={'pk': self.object.user.pk})

class AvailabilityDeleteView(LoginRequiredMixin, DeleteView):
    model = Availability
    template_name = 'accounts/delete_availability.html'

    def get_success_url(self):
        return reverse('view_availabilities', args=[self.object.user.pk])

class AvailabilityListView(LoginRequiredMixin, ListView):
    model = Availability
    template_name = 'accounts/view_availabilities.html'
    context_object_name = 'availabilities'

    def get_queryset(self):
        self.user = get_object_or_404(CustomUser, pk=self.kwargs['pk'])
        return Availability.objects.filter(user=self.user)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['user'] = self.user
        return context



class LogoutView(LoginRequiredMixin, APIView):
    permission_classes = [AllowAny]

    def post(self, request, *args, **kwargs):
        logout(request)
        return redirect('logout_confirmation')

def logout_confirmation_view(request):
    return render(request, 'accounts/logout_confirmation.html')




class ServiceConstraintsListView(ListView):
    model = ServiceConstraints
    template_name = 'accounts/service_constraints_list.html'
    context_object_name = 'constraints'

    def get_queryset(self):
        return ServiceConstraints.objects.filter(user=self.request.user)

class ServiceConstraintsCreateView(CreateView):
    model = ServiceConstraints
    form_class = ServiceConstraintsForm
    template_name = 'accounts/service_constraints_form.html'

    def get_context_data(self, **kwargs):
        data = super().get_context_data(**kwargs)
        if self.request.POST:
            data['shift_requirements'] = ShiftRequirementFormSet(self.request.POST)
        else:
            data['shift_requirements'] = ShiftRequirementFormSet()
        return data

    def form_valid(self, form):
        context = self.get_context_data()
        shift_requirements = context['shift_requirements']
        self.object = form.save()
        if shift_requirements.is_valid():
            shift_requirements.instance = self.object
            shift_requirements.save()
        return super().form_valid(form)

    def get_success_url(self):
        return reverse('constraints_list')

from django.utils.dateparse import parse_time

class ServiceConstraintsUpdateView(View):
    template_name = 'accounts/service_constraints_form.html'

    def get_object(self):
        return get_object_or_404(ServiceConstraints, user=self.request.user)

    def get(self, request, *args, **kwargs):
        obj = self.get_object()
        context = {
            'form': {
                'monday_start': obj.monday_start,
                'monday_end': obj.monday_end,
                'tuesday_start': obj.tuesday_start,
                'tuesday_end': obj.tuesday_end,
                'wednesday_start': obj.wednesday_start,
                'wednesday_end': obj.wednesday_end,
                'thursday_start': obj.thursday_start,
                'thursday_end': obj.thursday_end,
                'friday_start': obj.friday_start,
                'friday_end': obj.friday_end,
                'saturday_start': obj.saturday_start,
                'saturday_end': obj.saturday_end,
                'sunday_start': obj.sunday_start,
                'sunday_end': obj.sunday_end,
            }
        }
        return render(request, self.template_name, context)

    def post(self, request, *args, **kwargs):
        obj = self.get_object()
        
        fields_to_update = [
            'monday_start', 'monday_end',
            'tuesday_start', 'tuesday_end',
            'wednesday_start', 'wednesday_end',
            'thursday_start', 'thursday_end',
            'friday_start', 'friday_end',
            'saturday_start', 'saturday_end',
            'sunday_start', 'sunday_end',
        ]

        for field in fields_to_update:
            value = request.POST.get(field)
            if value:
                setattr(obj, field, parse_time(value))

        try:
            obj.save(update_fields=fields_to_update)
            messages.success(request, "Les horaires de travail ont été mis à jour avec succès.")
        except Exception as e:
            messages.error(request, f"Une erreur s'est produite lors de la mise à jour : {str(e)}")

        return redirect(reverse('constraints_list'))




class EmployeeRequirementCreateView(View):
    def get(self, request):
        days_of_week = [
            ('Monday', 'Lundi'),
            ('Tuesday', 'Mardi'),
            ('Wednesday', 'Mercredi'),
            ('Thursday', 'Jeudi'),
            ('Friday', 'Vendredi'),
            ('Saturday', 'Samedi'),
            ('Sunday', 'Dimanche'),
        ]
        return render(request, 'accounts/employee_requirement_form.html', {'days_of_week': days_of_week})

    def post(self, request):
        day_of_week = request.POST.get('day_of_week')
        start_times = request.POST.getlist('start_time[]')
        end_times = request.POST.getlist('end_time[]')
        employees_required = request.POST.getlist('employees_required[]')

        if day_of_week and start_times and end_times and employees_required:
            try:
                # Créer un nouvel EmployeeRequirement
                employee_requirement = EmployeeRequirement.objects.create(
                    user=request.user,
                    day_of_week=day_of_week,
                )

                # Créer les shifts associés
                for start_time, end_time, employees in zip(start_times, end_times, employees_required):
                    Shift.objects.create(
                        employee_requirement=employee_requirement,
                        start_time=start_time,
                        end_time=end_time,
                        employees_required=int(employees)
                    )

                messages.success(request, 'Les besoins en employés ont été ajoutés avec succès.')
                return redirect('manage_employee_requirements')  # Assurez-vous que ce nom d'URL est correct
            except Exception as e:
                print(f"Error creating EmployeeRequirement: {str(e)}")
                messages.error(request, f'Une erreur est survenue lors de l\'ajout des besoins en employés: {str(e)}')
        else:
            messages.error(request, 'Tous les champs doivent être remplis.')
        
        # Si une erreur s'est produite, redirigez vers la même page
        return render(request, 'accounts/employee_requirement_form.html', {
            'days_of_week': [
                ('Monday', 'Lundi'),
                ('Tuesday', 'Mardi'),
                ('Wednesday', 'Mercredi'),
                ('Thursday', 'Jeudi'),
                ('Friday', 'Vendredi'),
                ('Saturday', 'Samedi'),
                ('Sunday', 'Dimanche'),
            ],
            'form_data': request.POST,  # Renvoyer les données du formulaire pour les afficher
        })

class EmployeeRequirementListView(ListView):
    model = EmployeeRequirement
    template_name = 'accounts/employee_requirements_list.html'
    context_object_name = 'requirements'

    def get_queryset(self):
        queryset = EmployeeRequirement.objects.filter(user=self.request.user)
        print("DEBUG: queryset:", queryset)  
        return queryset

class EmployeeRequirementUpdateView(UpdateView):
    model = EmployeeRequirement
    template_name = 'accounts/employee_requirement_form.html'
    fields = []
    success_url = reverse_lazy('manage_employee_requirements')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['shifts'] = self.object.shifts.all()
        context['days_of_week'] = [
            ('Monday', 'Lundi'),
            ('Tuesday', 'Mardi'),
            ('Wednesday', 'Mercredi'),
            ('Thursday', 'Jeudi'),
            ('Friday', 'Vendredi'),
            ('Saturday', 'Samedi'),
            ('Sunday', 'Dimanche'),
        ]
        return context

    def form_valid(self, form):
        self.object = form.save(commit=False)
        day_of_week = self.request.POST.get('day_of_week')
        if day_of_week:
            self.object.day_of_week = day_of_week
            self.object.save()

        shift_ids = self.request.POST.getlist('shift_id[]')
        start_times = self.request.POST.getlist('start_time[]')
        end_times = self.request.POST.getlist('end_time[]')
        employees_required_list = self.request.POST.getlist('employees_required[]')

        for shift_id, start_time, end_time, employees_required in zip(shift_ids, start_times, end_times, employees_required_list):
            if shift_id:
                # Mettre à jour un shift existant
                shift = Shift.objects.get(id=int(shift_id))
                shift.start_time = start_time
                shift.end_time = end_time
                shift.employees_required = int(employees_required)  # Assurez-vous que cette ligne est présente
                shift.save()
            else:
                # Créer un nouveau shift seulement si tous les champs sont remplis
                if start_time and end_time and employees_required:
                    Shift.objects.create(
                        employee_requirement=self.object,
                        start_time=start_time,
                        end_time=end_time,
                        employees_required=int(employees_required)
                    )
        
        messages.success(self.request, 'Les besoins en employés ont été mis à jour avec succès.')
        return super().form_valid(form)

    def form_invalid(self, form):
        messages.error(self.request, 'Erreur lors de la mise à jour des besoins en employés. Veuillez vérifier les données saisies.')
        return super().form_invalid(form)

class EmployeeRequirementDeleteView(DeleteView):
    model = EmployeeRequirement
    template_name = 'accounts/employee_requirement_confirm_delete.html'
    success_url = reverse_lazy('manage_employee_requirements')

    def get_queryset(self):
        return EmployeeRequirement.objects.filter(user=self.request.user)



from datetime import datetime, time, timedelta
from django.utils import timezone



class GenerateScheduleView(View):
    def get(self, request):
        form = WeekSelectionForm()
        return render(request, 'accounts/generate_schedule.html', {'form': form})

    def post(self, request):
        form = WeekSelectionForm(request.POST)
        if form.is_valid():
            start_date = form.cleaned_data['start_date']
            end_date = start_date + timedelta(days=6)

            employees = list(CustomUser.objects.filter(created_by=request.user))
            logger.debug(f"Number of employees: {len(employees)}")

            availabilities = {e.id: list(Availability.objects.filter(user=e)) for e in employees}
            logger.debug(f"Availabilities: {availabilities}")

            constraints = ServiceConstraints.objects.filter(user=request.user).first()
            if not constraints:
                messages.error(request, 'Aucune contrainte de service définie.')
                return redirect('generate_schedule')

            constraints_data = {
                'shifts': [],
                'required_employees': [],
                'max_work_hours_per_day': int(constraints.max_work_hours_per_day),
                'max_consecutive_work_hours': int(constraints.max_consecutive_work_hours),
                'min_break_minutes': int(constraints.min_break_minutes),
                'min_consecutive_rest_days': int(constraints.min_consecutive_rest_days),
            }

            shift_requirements = {
                'Monday': list(EmployeeRequirement.objects.filter(day_of_week='Monday', user=request.user)),
                'Tuesday': list(EmployeeRequirement.objects.filter(day_of_week='Tuesday', user=request.user)),
                'Wednesday': list(EmployeeRequirement.objects.filter(day_of_week='Wednesday', user=request.user)),
                'Thursday': list(EmployeeRequirement.objects.filter(day_of_week='Thursday', user=request.user)),
                'Friday': list(EmployeeRequirement.objects.filter(day_of_week='Friday', user=request.user)),
                'Saturday': list(EmployeeRequirement.objects.filter(day_of_week='Saturday', user=request.user)),
                'Sunday': list(EmployeeRequirement.objects.filter(day_of_week='Sunday', user=request.user)),
            }

            for day, requirements in shift_requirements.items():
                day_shifts = []
                day_required_employees = []
                for requirement in requirements:
                    for shift in requirement.shifts.all():
                        day_shifts.append((shift.start_time, shift.end_time))
                        day_required_employees.append(int(shift.employees_required))
                constraints_data['shifts'].append((day, day_shifts))
                constraints_data['required_employees'].append(day_required_employees)

            logger.debug(f"Constraints data: {constraints_data}")

            try:
                schedule, detailed_messages = generate_schedule(employees, availabilities, constraints_data, start_date, end_date)
            except Exception as e:
                logger.exception("Error in generate_schedule")
                messages.error(request, f"Erreur lors de la génération du planning: {str(e)}")
                return redirect('generate_schedule')

            if schedule is None:
                messages.error(request, 'Impossible de générer un planning valide avec les contraintes actuelles.')
                for msg in detailed_messages:
                    messages.warning(request, msg)
                return render(request, 'accounts/generate_schedule.html', {
                    'form': form,
                    'detailed_messages': detailed_messages,
                    'constraints_data': constraints_data,
                    'availabilities': availabilities
                })

            messages.success(request, 'Le planning a été généré avec succès.')

            new_schedule = Schedule.objects.create(
                user=request.user,
                start_date=start_date,
                end_date=end_date
            )
            
            total_hours_per_day = {}
            total_hours_per_week = {}

            for entry in schedule:
                ScheduleEntry.objects.create(
                    schedule=new_schedule,
                    employee=entry['employee'],
                    day=entry['day'],
                    start_time=entry['start_time'],
                    end_time=entry['end_time'],
                    hours=entry['hours']
                )

                employee = entry['employee']
                employee_name = f"{employee.first_name} {employee.last_name}"
                day = entry['day']
                hours = entry['hours']

                if employee_name not in total_hours_per_day:
                    total_hours_per_day[employee_name] = {}
                if day not in total_hours_per_day[employee_name]:
                    total_hours_per_day[employee_name][day] = 0
                total_hours_per_day[employee_name][day] += hours

                if employee_name not in total_hours_per_week:
                    total_hours_per_week[employee_name] = 0
                total_hours_per_week[employee_name] += hours

            return render(request, 'accounts/generate_schedule.html', {
                'form': form,
                'schedule': schedule,
                'start_date': start_date,
                'end_date': end_date,
                'total_hours_per_day': total_hours_per_day,
                'total_hours_per_week': total_hours_per_week
            })

        else:
            messages.error(request, 'Formulaire invalide. Veuillez réessayer.')
        return render(request, 'accounts/generate_schedule.html', {'form': form})




from django.views.decorators.csrf import csrf_exempt


@csrf_exempt
@login_required
def send_schedule_notifications(request):
    if request.method == "POST":
        data = json.loads(request.body)
        message = data.get("message", "")

        # Envoyer une notification à tous les employés, sauf les managers
        employees = CustomUser.objects.filter(role='employee')
        for employee in employees:
            Notification.objects.create(
                user=employee,
                message=message
            )

        return JsonResponse({"status": "success"}, status=200)
    return JsonResponse({"status": "error"}, status=400)




def get_current_week_dates():
    today = datetime.now().date()
    start_of_week = today - timedelta(days=today.weekday())
    end_of_week = start_of_week + timedelta(days=6)
    return start_of_week, end_of_week

class ViewScheduleView(View):
    def get(self, request):
        form = WeekSelectionForm()
        user = request.user
        
        if user.role == 'manager':
            employees = CustomUser.objects.filter(created_by=user)
        else:
            # Obtenir tous les employés créés par le même manager que l'utilisateur actuel
            employees = CustomUser.objects.filter(created_by=user.created_by)
        
        start_date, end_date = get_current_week_dates()
        
        context = self.get_schedule_context(user, employees, start_date, end_date)
        context['form'] = form
        
        return render(request, 'accounts/view_schedule.html', context)

    def post(self, request):
        form = WeekSelectionForm(request.POST)
        user = request.user
        
        if user.role == 'manager':
            employees = CustomUser.objects.filter(created_by=user)
        else:
            employees = [user]

        if form.is_valid():
            start_date = form.cleaned_data['start_date']
            end_date = start_date + timedelta(days=6)

            context = self.get_schedule_context(user, employees, start_date, end_date)
            if context.get('employee_schedules'):
                context['form'] = form
                return render(request, 'accounts/view_schedule.html', context)
            else:
                messages.error(request, 'Pas de planning pour cette semaine.')
        else:
            messages.error(request, 'Formulaire invalide. Veuillez réessayer.')

        return render(request, 'accounts/view_schedule.html', {'form': form, 'employees': employees})

    def get_schedule_context(self, user, employees, start_date, end_date):
        logger.debug(f"Searching for schedule: start_date={start_date}, end_date={end_date}")
        schedule = Schedule.objects.filter(
            user=user.created_by if user.role != 'manager' else user,
            start_date=start_date,
            end_date=end_date
        ).order_by('-id').first()

        context = {'employees': employees, 'start_date': start_date, 'end_date': end_date}

        if schedule:
            logger.debug(f"Found schedule: id={schedule.id}, start_date={schedule.start_date}, end_date={schedule.end_date}")
            employee_schedules, employee_total_hours = self.process_schedule(schedule, employees)
            context.update({
                'employee_schedules': employee_schedules,
                'employee_total_hours': employee_total_hours,
                'days': ["Lundi", "Mardi", "Mercredi", "Jeudi", "Vendredi", "Samedi", "Dimanche"],
            })
        else:
            logger.debug("No schedule found for the specified dates")

        return context

    def process_schedule(self, schedule, employees):
        day_translation = {
            'Monday': 'Lundi', 'Tuesday': 'Mardi', 'Wednesday': 'Mercredi',
            'Thursday': 'Jeudi', 'Friday': 'Vendredi', 'Saturday': 'Samedi', 'Sunday': 'Dimanche'
        }
        days = ["Lundi", "Mardi", "Mercredi", "Jeudi", "Vendredi", "Samedi", "Dimanche"]
        
        employee_schedules = {employee.pk: {day: [] for day in days} for employee in employees}
        employee_total_hours = {employee.pk: 0 for employee in employees}

        schedule_entries = schedule.entries.all()
        logger.debug(f"Number of Schedule Entries: {schedule_entries.count()}")

        for entry in schedule_entries:
            logger.debug(f"Entry: Employee {entry.employee.pk}, Day {entry.day}, Start {entry.start_time}, End {entry.end_time}")
            
            employee = entry.employee
            if employee.pk not in employee_schedules:
                employee_schedules[employee.pk] = {day: [] for day in days}
                employee_total_hours[employee.pk] = 0
            
            day_french = day_translation.get(entry.day, entry.day)
            employee_schedules[employee.pk][day_french].append({
                'start_time': entry.start_time.strftime('%H:%M'),
                'end_time': entry.end_time.strftime('%H:%M'),
                'hours': entry.hours
            })
            employee_total_hours[employee.pk] += entry.hours

        # Trier les shifts pour chaque employé et chaque jour
        for employee_id in employee_schedules:
            for day in days:
                employee_schedules[employee_id][day].sort(key=lambda x: x['start_time'])

        return employee_schedules, employee_total_hours







    
from xhtml2pdf import pisa  # Modifié cette ligne
from django.http import HttpResponse  # Assurez-vous que cet import est correct


def render_to_pdf(template_src, context_dict={}):
    template = get_template(template_src)
    html = template.render(context_dict)
    result = BytesIO()
    pdf = pisa.pisaDocument(BytesIO(html.encode("ISO-8859-1")), result)
    if not pdf.err:
        return result.getvalue()
    return None

def download_schedule_pdf(request):
    start_date = request.GET.get('start_date')
    if start_date:
        start_date = timezone.datetime.strptime(start_date, '%Y-%m-%d').date()
    else:
        start_date = timezone.now().date()
    
    end_date = start_date + timedelta(days=6)
    
    manager = request.user
    employees = CustomUser.objects.filter(created_by=manager)
    schedule = Schedule.objects.filter(start_date=start_date, end_date=end_date).order_by('-id').first()
    
    if not schedule:
        return HttpResponse("Pas de planning pour cette semaine.", status=404)
    
    schedule_entries = ScheduleEntry.objects.filter(schedule=schedule)
    
    days = ["Lundi", "Mardi", "Mercredi", "Jeudi", "Vendredi", "Samedi", "Dimanche"]
    
    employee_schedules = []
    for employee in employees:
        employee_schedule = {
            'name': f"{employee.first_name} {employee.last_name}",
            'shifts': [],
            'total_hours': 0
        }
        for day in days:
            shifts = schedule_entries.filter(employee=employee, day=day).order_by('start_time')
            day_shifts = []
            for shift in shifts:
                day_shifts.append({
                    'start_time': shift.start_time.strftime('%H:%M'),
                    'end_time': shift.end_time.strftime('%H:%M'),
                    'hours': shift.hours
                })
                employee_schedule['total_hours'] += shift.hours
            employee_schedule['shifts'].append({
                'day': day,
                'shifts': day_shifts
            })
        employee_schedule['total_hours'] = round(employee_schedule['total_hours'], 2)
        employee_schedules.append(employee_schedule)
    
    context = {
        'employee_schedules': employee_schedules,
        'days': days,
        'start_date': start_date,
        'end_date': end_date,
    }
    
    pdf = render_to_pdf('accounts/schedule_pdf_template.html', context)
    if pdf:
        response = HttpResponse(pdf, content_type='application/pdf')
        filename = f"planning_{start_date}.pdf"
        response['Content-Disposition'] = f'attachment; filename="{filename}"'
        return response
    return HttpResponse("Error generating PDF", status=400)

def render_to_pdf(template_src, context_dict={}):
    template = get_template(template_src)
    html = template.render(context_dict)
    result = BytesIO()
    pdf = pisa.pisaDocument(BytesIO(html.encode("ISO-8859-1")), result)
    if not pdf.err:
        return result.getvalue()
    return None
from .models import Schedule, ScheduleEntry

from .forms import ShiftForm

def modify_shift(request, employee_id, day):
    start_date = request.GET.get('start_date')
    if start_date:
        start_date = timezone.datetime.strptime(start_date, '%Y-%m-%d').date()
    else:
        start_date = timezone.now().date()
    
    end_date = start_date + timezone.timedelta(days=6)
    schedule = Schedule.objects.filter(start_date=start_date, end_date=end_date).first()
    
    if not schedule:
        return HttpResponse("Pas de planning pour cette semaine.", status=404)
    
    entry = ScheduleEntry.objects.filter(schedule=schedule, employee_id=employee_id, day=day).first()
    
    if request.method == 'POST':
        form = ShiftForm(request.POST, instance=entry)
        if form.is_valid():
            form.save()
            return redirect('view_schedule')
    else:
        form = ShiftForm(instance=entry) if entry else ShiftForm()

    context = {
        'form': form,
        'employee': CustomUser.objects.get(id=employee_id),
        'day': day,
        'start_date': start_date
    }
    return render(request, 'accounts/modify_shift.html', context)




def add_shift(request, employee_id, day):
    start_date = request.GET.get('start_date')
    if start_date:
        start_date = timezone.datetime.strptime(start_date, '%Y-%m-%d').date()
    else:
        start_date = timezone.now().date()
    
    end_date = start_date + timezone.timedelta(days=6)
    schedule = Schedule.objects.filter(start_date=start_date, end_date=end_date).first()
    
    if not schedule:
        return HttpResponse("Pas de planning pour cette semaine.", status=404)
    
    if request.method == 'POST':
        form = ShiftForm(request.POST)
        if form.is_valid():
            entry = form.save(commit=False)
            entry.schedule = schedule
            entry.employee_id = employee_id
            entry.day = day
            entry.save()
            return redirect('view_schedule')
    else:
        form = ShiftForm()

    context = {
        'form': form,
        'employee': CustomUser.objects.get(id=employee_id),
        'day': day,
        'start_date': start_date
    }
    return render(request, 'accounts/add_shift.html', context)

from django.http import JsonResponse
import json
from datetime import timedelta

from django.views.decorators.csrf import csrf_exempt
from django.utils.dateparse import parse_date, parse_time

from django.db import transaction







class UpdateScheduleView(View):
    @transaction.atomic
    def post(self, request):
        try:
            data = json.loads(request.body)
            shifts = data.get('shifts', [])
            start_date = parse_date(data.get('start_date'))
            
            if not start_date:
                return JsonResponse({'success': False, 'message': 'Date de début invalide'}, status=400)

            end_date = start_date + timedelta(days=6)
            
            # Récupérer l'ancien planning
            old_schedule = Schedule.objects.filter(
                start_date=start_date,
                end_date=end_date
            ).first()

            old_entries = {}
            if old_schedule:
                for entry in ScheduleEntry.objects.filter(schedule=old_schedule):
                    key = (entry.employee_id, entry.day)
                    if key not in old_entries:
                        old_entries[key] = []
                    old_entries[key].append(entry)

            # Supprimer l'ancien planning
            if old_schedule:
                old_schedule.delete()

            # Créer un nouveau planning
            schedule = Schedule.objects.create(
                user=request.user,
                start_date=start_date,
                end_date=end_date
            )

            modified_employees = set()

            for shift in shifts:
                employee = CustomUser.objects.get(id=shift['employeeId'])
                start_time = parse_time(shift['startTime'])
                end_time = parse_time(shift['endTime'])

                if not start_time or not end_time:
                    continue  # Ignorer les entrées de temps invalides

                hours = (end_time.hour - start_time.hour) + (end_time.minute - start_time.minute) / 60

                new_entry = ScheduleEntry.objects.create(
                    schedule=schedule,
                    employee=employee,
                    day=shift['day'],
                    start_time=start_time,
                    end_time=end_time,
                    hours=hours
                )

                # Vérifier si l'horaire a changé pour cet employé ce jour-là
                key = (employee.id, shift['day'])
                if key not in old_entries or not any(
                    old_entry.start_time == new_entry.start_time and
                    old_entry.end_time == new_entry.end_time
                    for old_entry in old_entries[key]
                ):
                    modified_employees.add(employee)

            # Créer des notifications uniquement pour les employés dont le planning a été modifié
            for employee in modified_employees:
                Notification.objects.create(
                    user=employee,
                    message=f"Votre planning pour la semaine du {start_date} au {end_date} a été modifié."
                )

            return JsonResponse({'success': True})
        except Exception as e:
            return JsonResponse({'success': False, 'message': str(e)}, status=400)


class SubmitLeaveRequestView(View):
    def get(self, request):
        form = LeaveRequestForm()
        return render(request, 'accounts/submit_leave_request.html', {'form': form})

    def post(self, request):
        form = LeaveRequestForm(request.POST)
        if form.is_valid():
            leave_request = form.save(commit=False)
            leave_request.user = request.user
            leave_request.save()

            # Create a notification for the manager
            managers = CustomUser.objects.filter(role='manager')
            for manager in managers:
                Notification.objects.create(
                    user=manager,
                    message=f"{request.user.username} a demandé un congé du {leave_request.start_date} au {leave_request.end_date}.",
                    notification_type='leave_request',  # Ajoutez cette ligne
                    redirect_url=reverse('manager_leave_requests')  # Ajoutez cette ligne si nécessaire
                )

            messages.success(request, 'Votre demande de congé a été soumise avec succès.')
            return redirect('home')
        else:
            messages.error(request, 'Veuillez corriger les erreurs ci-dessous.')
        return render(request, 'accounts/submit_leave_request.html', {'form': form})



class LeaveRequestListView(View):
    def get(self, request):
        leave_requests = LeaveRequest.objects.filter(user=request.user)
        leave_request_updated = request.session.pop('leave_request_updated', None)
        return render(request, 'accounts/leave_request_list.html', {'leave_requests': leave_requests, 'leave_request_updated': leave_request_updated})



class ManagerLeaveRequestsView(View):
    def get(self, request):
        leave_requests = LeaveRequest.objects.filter(user__created_by=request.user)
        return render(request, 'accounts/manager_leave_requests.html', {'leave_requests': leave_requests})


class UpdateLeaveRequestStatusView(View):
    def post(self, request, pk):
        leave_request = get_object_or_404(LeaveRequest, pk=pk)
        status = request.POST.get('status')
        comments = request.POST.get('comments')
        if status in ['approved', 'rejected']:
            leave_request.status = status
            leave_request.comments = comments
            leave_request.save()

            # Créer une notification pour l'employé
            message = f"Votre manager a répondu à votre demande de congé du {leave_request.start_date} au {leave_request.end_date}. Vérifiez l'historique pour plus de détails."
            Notification.objects.create(user=leave_request.user, message=message)

            messages.success(request, 'Le statut de la demande a été mis à jour.')
        else:
            messages.error(request, 'Statut invalide.')
        return redirect('manager_leave_requests')

        
class UpdateLeaveRequestView(View):
    def get(self, request, pk):
        leave_request = get_object_or_404(LeaveRequest, pk=pk)
        form = UpdateLeaveRequestForm(instance=leave_request)
        return render(request, 'accounts/update_leave_request.html', {'form': form, 'leave_request': leave_request})

    def post(self, request, pk):
        leave_request = get_object_or_404(LeaveRequest, pk=pk)
        form = UpdateLeaveRequestForm(request.POST, instance=leave_request)
        if form.is_valid():
            form.save()
            # Créer une notification pour le manager
            message = f"La demande de congé de {leave_request.user.username} du {leave_request.start_date} au {leave_request.end_date} a été modifiée."
            Notification.objects.create(user=leave_request.user.created_by, message=message)
            request.session['leave_request_updated'] = True
            return redirect('leave_request_list')
        else:
            messages.error(request, 'Veuillez corriger les erreurs ci-dessous.')
        return render(request, 'accounts/update_leave_request.html', {'form': form, 'leave_request': leave_request})


    
class CancelLeaveRequestView(View):
    def post(self, request, pk):
        leave_request = get_object_or_404(LeaveRequest, pk=pk)
        if leave_request.status == 'pending':
            leave_request.delete()
            # Créer une notification pour le manager
            message = f"La demande de congé de {leave_request.user.username} du {leave_request.start_date} au {leave_request.end_date} a été annulée."
            Notification.objects.create(user=leave_request.user.created_by, message=message)
            messages.success(request, 'Votre demande de congé a été annulée avec succès.')
        return redirect('leave_request_list')



class NotificationListView(View):
    def get(self, request):
        notifications = Notification.objects.filter(user=request.user)
        unread_count = notifications.filter(is_read=False).count()
        # Mark all notifications as read
        notifications.update(is_read=True)
        return render(request, 'accounts/notification_list.html', {'notifications': notifications, 'unread_count': unread_count})
    



class PointageView(LoginRequiredMixin, View):
    template_name = 'accounts/pointage.html'

    def get(self, request):
        return render(request, self.template_name)

    def post(self, request):
        code = request.POST.get('pointage_code')
        try:
            user = CustomUser.objects.get(pointage_code=code)
            if 'team_lead' in request.POST:
                if user.role == 'team_lead':
                    return redirect('team_lead_pointage')
                else:
                    messages.error(request, 'Code de chef d\'équipe invalide.')
                    return redirect('pointage')

            active_clock_in = TimeClock.objects.filter(user=user, clock_out_time__isnull=True).first()

            # Ajout d'une vérification pour clock_in_time
            if active_clock_in and active_clock_in.clock_in_time is None:
                messages.error(request, f'Erreur interne : l\'heure de pointage d\'entrée est manquante pour {user.username}.')
                return redirect('pointage')

            last_clock_out = TimeClock.objects.filter(user=user, clock_out_time__isnull=False).order_by('-clock_out_time').first()

            if 'clock_in' in request.POST:
                if not active_clock_in:
                    if last_clock_out and last_clock_out.clock_out_time:
                        if timezone.now() - last_clock_out.clock_out_time < timedelta(minutes=30):
                            messages.error(request, 'Vous devez attendre 30 minutes après votre dernier dépointe avant de pointer de nouveau.')
                            return redirect('pointage')
                    # Enregistre l'heure actuelle comme heure de pointage
                    TimeClock.objects.create(user=user, clock_in_time=timezone.now())
                    messages.success(request, f'{user.username} a pointé avec succès à {timezone.now().strftime("%H:%M")}.')
                else:
                    messages.error(request, f'{user.username} a déjà pointé.')
            elif 'clock_out' in request.POST:
                if active_clock_in:
                    if active_clock_in.clock_in_time and (timezone.now() - active_clock_in.clock_in_time < timedelta(hours=2)):
                        messages.error(request, 'Vous devez travailler pendant au moins 2 heures avant de dépointer.')
                        return redirect('pointage')
                    active_clock_in.clock_out_time = timezone.now()
                    active_clock_in.save()
                    messages.success(request, f'{user.username} a déponté avec succès à {timezone.now().strftime("%H:%M")}.')
                else:
                    messages.error(request, f'{user.username} doit pointer d\'abord.')
        except CustomUser.DoesNotExist:
            messages.error(request, 'Code de pointage invalide.')

        return redirect('pointage')



class DeleteEmployeeView(LoginRequiredMixin, View):
    def post(self, request, pk):
        employee = get_object_or_404(CustomUser, pk=pk)
        employee.delete()
        messages.success(request, "L'employé a été supprimé avec succès.")
        return redirect('employee_list') 


class DeleteTeamLeadView(View):
    def post(self, request, pk):
        team_lead = get_object_or_404(CustomUser, pk=pk, role='team_lead')
        team_lead.delete()
        messages.success(request, 'Le chef d\'équipe a été supprimé avec succès.')
        return redirect('team_lead_list') 






class TeamLeadPointageView(LoginRequiredMixin, View):
    template_name = 'accounts/team_lead_pointage.html'

    def get(self, request):
        # Le manager est l'utilisateur connecté
        manager = request.user

        # Récupérer tous les employés créés par le manager
        team_members = CustomUser.objects.filter(created_by=manager)

        # Récupérer tous les employés actuellement pointés
        clocked_in_employees = TimeClock.objects.filter(user__in=team_members, clock_out_time__isnull=True)

        return render(request, self.template_name, {
            'team_members': team_members,
            'clocked_in_employees': clocked_in_employees
        })

    def post(self, request):
        action = request.POST.get('action')

        if 'clock_in' in action or 'clock_out' in action:
            employee_id = request.POST.get('employee_id')
            datetime_str = request.POST.get('time')

            try:
                manager = request.user
                user = CustomUser.objects.get(id=employee_id, created_by=manager)

                # Gestion flexible du format de l'heure
                if datetime_str:
                    try:
                        # Essayer d'abord le format complet
                        datetime_value = timezone.make_aware(datetime.strptime(datetime_str, '%Y-%m-%dT%H:%M'), timezone.get_current_timezone())
                    except ValueError:
                        # Si ça échoue, essayer le format d'heure simple
                        time_obj = datetime.strptime(datetime_str, '%H:%M').time()
                        current_date = timezone.now().date()
                        datetime_value = timezone.make_aware(datetime.combine(current_date, time_obj), timezone.get_current_timezone())
                else:
                    datetime_value = timezone.now()

                if 'clock_in' in action:
                    active_clock_in = TimeClock.objects.filter(user=user, clock_out_time__isnull=True).first()
                    if not active_clock_in:
                        TimeClock.objects.create(user=user, clock_in_time=datetime_value)
                        messages.success(request, f'{user.username} a pointé avec succès.')
                    else:
                        messages.error(request, f'{user.username} est déjà pointé.')
                elif 'clock_out' in action:
                    active_clock_in = TimeClock.objects.filter(user=user, clock_out_time__isnull=True).first()
                    if active_clock_in:
                        if datetime_value < active_clock_in.clock_in_time:
                            messages.error(request, 'Le temps de dépointe doit être après le temps de pointe.')
                        else:
                            active_clock_in.clock_out_time = datetime_value
                            active_clock_in.save()
                            messages.success(request, f'{user.username} a déponté avec succès.')
                    else:
                        messages.error(request, f'{user.username} doit pointer d\'abord.')
            except CustomUser.DoesNotExist:
                messages.error(request, 'Employé invalide ou non autorisé.')
            except ValueError as e:
                messages.error(request, f'Format d\'heure invalide : {str(e)}')


        # Pour l'édition ou la suppression d'un pointage
        elif 'edit_' in action:
            clock_in_id = int(action.split('_')[1])
            new_time_str = request.POST.get(f'clock_in_time_{clock_in_id}')
            if new_time_str:
                clock_in_record = TimeClock.objects.get(id=clock_in_id)
                # Conserver la date d'origine, mais mettre à jour l'heure
                original_date = clock_in_record.clock_in_time.date()
                new_time = datetime.strptime(new_time_str, '%H:%M').time()
                new_datetime = datetime.combine(original_date, new_time)
                clock_in_record.clock_in_time = timezone.make_aware(new_datetime, timezone.get_current_timezone())
                clock_in_record.save()
                messages.success(request, 'Le pointage a été modifié avec succès.')
            else:
                messages.error(request, 'Heure de pointage invalide.')

        elif 'delete_' in action:
            clock_in_id = int(action.split('_')[1])
            clock_in_record = TimeClock.objects.get(id=clock_in_id)
            clock_in_record.delete()
            messages.success(request, 'Le pointage a été supprimé avec succès.')

        return redirect('team_lead_pointage')



class EditTimeClockView(LoginRequiredMixin, View):
    def get(self, request, clock_in_id):
        clock_in = get_object_or_404(TimeClock, id=clock_in_id)
        return render(request, 'accounts/edit_timeclock.html', {'clock_in': clock_in})

    def post(self, request, clock_in_id):
        clock_in = get_object_or_404(TimeClock, id=clock_in_id)
        new_time = request.POST.get('clock_in_time')
        if new_time:
            clock_in.clock_in_time = timezone.make_aware(datetime.strptime(new_time, '%Y-%m-%dT%H:%M'), timezone.get_current_timezone())
            clock_in.save()
            messages.success(request, 'Le pointage a été modifié avec succès.')
        else:
            messages.error(request, 'Veuillez fournir une date et une heure valides.')
        return redirect('team_lead_pointage')
    
class DeleteTimeClockView(LoginRequiredMixin, View):
    def post(self, request, clock_in_id):
        clock_in = get_object_or_404(TimeClock, id=clock_in_id)
        clock_in.delete()
        messages.success(request, 'Le pointage a été supprimé avec succès.')
        return redirect('team_lead_pointage')

    

class WorkHoursView(LoginRequiredMixin, View):
    template_name = 'accounts/work_hours.html'

    def get(self, request):
        return render(request, self.template_name)

class WorkHoursDetailView(LoginRequiredMixin, View):
    def post(self, request):
        user = request.user
        period = request.POST.get('period')
        work_hours = []
        total_hours = 0

        if period == 'weekly':
            week = request.POST.get('week')
            if week:
                year, week_number = week.split('-W')
                start_date = datetime.strptime(f"{year}-W{week_number}-1", "%Y-W%W-%w").date()
            else:
                start_date = timezone.now().date() - timezone.timedelta(days=timezone.now().weekday())
            end_date = start_date + timezone.timedelta(days=6)
        elif period == 'monthly':
            month = request.POST.get('month')
            if month:
                start_date = datetime.strptime(month, '%Y-%m').date()
            else:
                start_date = timezone.now().date().replace(day=1)
            end_date = (start_date + timezone.timedelta(days=32)).replace(day=1) - timezone.timedelta(days=1)

        time_clocks = TimeClock.objects.filter(user=user, clock_in_time__date__range=(start_date, end_date))

        for date in (start_date + timezone.timedelta(n) for n in range((end_date - start_date).days + 1)):
            daily_hours = sum(
                (clock_out_time - clock_in_time).total_seconds() / 3600 for clock_in_time, clock_out_time in
                time_clocks.filter(clock_in_time__date=date).exclude(clock_out_time__isnull=True).values_list('clock_in_time', 'clock_out_time')
            )
            work_hours.append({'date': date, 'hours': daily_hours})
            total_hours += daily_hours

        return render(request, 'accounts/work_hours_detail.html', {
            'work_hours': work_hours,
            'period': period,
            'start_date': start_date,
            'end_date': end_date,
            'total_hours': total_hours
        })
    
from django.db.models import Sum, F

class ManagerEmployeeHoursView(LoginRequiredMixin, View):
    template_name = 'accounts/manager_employee_hours.html'

    def get(self, request):
        current_month = timezone.now().strftime('%Y-%m')
        return render(request, self.template_name, {'current_month': current_month})

    def post(self, request):
        month = request.POST.get('month')
        search_term = request.POST.get('search', '').strip()

        if month:
            start_date = datetime.strptime(month, '%Y-%m').date()
            end_date = (start_date.replace(day=28) + timezone.timedelta(days=4)).replace(day=1) - timezone.timedelta(days=1)

            employees = CustomUser.objects.filter(created_by=request.user)
            if search_term:
                employees = employees.filter(Q(first_name__icontains=search_term) | Q(last_name__icontains=search_term))

            employee_hours = []

            for employee in employees:
                total_hours = TimeClock.objects.filter(
                    user=employee,
                    clock_in_time__date__gte=start_date,
                    clock_in_time__date__lte=end_date,
                    clock_out_time__isnull=False
                ).aggregate(
                    total_hours=Sum(F('clock_out_time') - F('clock_in_time'))
                )['total_hours'] or timezone.timedelta()

                employee_hours.append({
                    'id': employee.id,
                    'name': f"{employee.first_name} {employee.last_name}",
                    'role': employee.get_role_display(),
                    'hours': total_hours.total_seconds() / 3600,
                    'detail_url': reverse('employee_hours_detail', kwargs={'employee_id': employee.id, 'year': start_date.year, 'month': start_date.month})
                })

            context = {
                'employee_hours': employee_hours,
                'month_display': start_date.strftime('%B %Y'),
                'month': month,
                'current_month': month,
                'search_term': search_term
            }
            return render(request, self.template_name, context)

        return render(request, self.template_name, {'current_month': timezone.now().strftime('%Y-%m')})
    






import time

class EmployeeHoursDetailView(LoginRequiredMixin, View):
    template_name = 'accounts/employee_hours_detail.html'

    def get(self, request, employee_id, year, month):
        employee = get_object_or_404(CustomUser, id=employee_id, created_by=request.user)
        start_date = datetime(year, month, 1).date()
        end_date = (start_date.replace(day=28) + timezone.timedelta(days=4)).replace(day=1) - timezone.timedelta(days=1)

        time_clocks = TimeClock.objects.filter(
            user=employee,
            clock_in_time__date__gte=start_date,
            clock_in_time__date__lte=end_date
        ).order_by('clock_in_time')

        context = {
            'employee': employee,
            'time_clocks': time_clocks,
            'month_display': start_date.strftime('%B %Y'),
            'year': year,
            'month': month,
        }
        return render(request, self.template_name, context)

    def post(self, request, employee_id, year, month):
        print("Received POST data:", request.POST)
        employee = get_object_or_404(CustomUser, id=employee_id, created_by=request.user)
        time_clock_id = request.POST.get('time_clock_id')
        action = request.POST.get('action')

        print(f"Action: {action}, TimeClock ID: {time_clock_id}")

        if action == 'edit':
            return self.handle_edit(request, employee, time_clock_id)
        elif action == 'delete':
            return self.handle_delete(request, employee, time_clock_id, year, month)
        else:
            print("Unrecognized action")
            return redirect('employee_hours_detail', employee_id=employee_id, year=year, month=month)

    def handle_edit(self, request, employee, time_clock_id):
        clock_in_time = request.POST.get('clock_in_time')
        clock_out_time = request.POST.get('clock_out_time')
        clock_date = request.POST.get('clock_date')

        try:
            if time_clock_id:  # Modifier un enregistrement existant
                time_clock = get_object_or_404(TimeClock, id=time_clock_id, user=employee)
            else:  # Créer un nouveau pointage
                time_clock = TimeClock(user=employee)

            if clock_date:
                clock_date = datetime.strptime(clock_date, '%Y-%m-%d').date()
                if clock_in_time:
                    naive_datetime = datetime.combine(clock_date, datetime.strptime(clock_in_time, '%H:%M').time())
                    time_clock.clock_in_time = timezone.make_aware(naive_datetime)
                if clock_out_time:
                    naive_datetime = datetime.combine(clock_date, datetime.strptime(clock_out_time, '%H:%M').time())
                    time_clock.clock_out_time = timezone.make_aware(naive_datetime)

            time_clock.save()
            return JsonResponse({'success': True, 'message': 'Enregistrement sauvegardé avec succès.'})
        except Exception as e:
            print(f"Error during edit: {str(e)}")
            return JsonResponse({'success': False, 'message': f'Erreur lors de la sauvegarde: {str(e)}'}, status=500)

    def handle_delete(self, request, employee, time_clock_id, year, month):
        print(f"Attempting to delete TimeClock with ID: {time_clock_id}")
        if not time_clock_id or time_clock_id in ['null', 'undefined']:
            return JsonResponse({'success': False, 'message': 'ID d\'enregistrement invalide.'}, status=400)
        
        try:
            time_clock_id = int(time_clock_id)
        except ValueError:
            return JsonResponse({'success': False, 'message': 'ID d\'enregistrement non valide.'}, status=400)

        max_attempts = 3
        for attempt in range(max_attempts):
            try:
                with transaction.atomic():
                    time_clock = TimeClock.objects.select_for_update(nowait=True).get(id=time_clock_id, user=employee)
                    time_clock.delete()
                print(f"Successfully deleted TimeClock with ID: {time_clock_id}")
                current_url = reverse('employee_hours_detail', kwargs={'employee_id': employee.id, 'year': year, 'month': month})
                return JsonResponse({
                    'success': True, 
                    'message': 'Enregistrement supprimé avec succès.',
                    'redirect_url': current_url
                })
            except TimeClock.DoesNotExist:
                print(f"TimeClock with ID {time_clock_id} not found")
                return JsonResponse({'success': False, 'message': 'Enregistrement non trouvé.'}, status=404)
            except OperationalError as e:
                if 'database is locked' in str(e) and attempt < max_attempts - 1:
                    print(f"Database locked, retrying (attempt {attempt + 1})")
                    time.sleep(0.5)  # Wait for 0.5 seconds before retrying
                else:
                    print(f"Error during deletion of TimeClock {time_clock_id}: {str(e)}")
                    return JsonResponse({'success': False, 'message': f'Erreur lors de la suppression: {str(e)}'}, status=500)
            except Exception as e:
                print(f"Error during deletion of TimeClock {time_clock_id}: {str(e)}")
                return JsonResponse({'success': False, 'message': f'Erreur lors de la suppression: {str(e)}'}, status=500)

        return JsonResponse({'success': False, 'message': 'Échec de la suppression après plusieurs tentatives.'}, status=500)
    

    