from django import forms
from django.contrib.auth.forms import UserCreationForm
from .models import CustomUser, Availability, LeaveRequest, ServiceConstraints,EmployeeRequirement,Shift,ShiftRequirement
from django.forms import inlineformset_factory
from django.utils import timezone

class SignUpForm(UserCreationForm):
    email = forms.EmailField(required=True, help_text='Required')

    class Meta:
        model = CustomUser
        fields = ('username', 'email', 'password1', 'password2', 'first_name', 'last_name')

    def save(self, commit=True):
        user = super().save(commit=False)
        user.role = 'manager'
        if commit:
            user.save()
        return user

class ManagerCreateUserForm(UserCreationForm):
    email = forms.EmailField(required=True)
    hours_per_week = forms.IntegerField(required=True, min_value=0, help_text='Heures de travail par semaine')
    photo = forms.ImageField(required=False, help_text='Photo de profil')

    class Meta:
        model = CustomUser
        fields = ('username', 'first_name', 'last_name', 'email', 'password1', 'password2', 'role', 'hours_per_week', 'photo')

    def clean_email(self):
        email = self.cleaned_data.get('email')
        if CustomUser.objects.filter(email=email).exists():
            raise forms.ValidationError("Cet email est déjà utilisé.")
        return email

class EmployeeEditForm(forms.ModelForm):
    email = forms.EmailField(required=True)
    photo = forms.ImageField(required=False)

    class Meta:
        model = CustomUser
        fields = ('username', 'email', 'first_name', 'last_name', 'role', 'hours_per_week', 'photo')
        widgets = {
            'role': forms.Select(choices=[('employee', 'Employé'), ('team_lead', 'Chef d\'équipe')]),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['photo'].widget.attrs.update({'class': 'form-control'})

    def clean_photo(self):
        photo = self.cleaned_data.get('photo')
        if not photo:
            return self.instance.photo  # Retourne la photo existante si aucune nouvelle photo n'est téléchargée
        return photo

class TeamLeadEditForm(forms.ModelForm):
    email = forms.EmailField(required=True)

    class Meta:
        model = CustomUser
        fields = ('username', 'email', 'first_name', 'last_name', 'role','hours_per_week')
        widgets = {
            'role': forms.Select(choices=[('employee', 'Employé'), ('team_lead', 'Chef d\'équipe')]),
        }

class AvailabilityForm(forms.ModelForm):
    class Meta:
        model = Availability
        fields = ['day_of_week', 'start_time', 'end_time']

class ServiceConstraintsForm(forms.ModelForm):
    class Meta:
        model = ServiceConstraints
        fields = [
            'monday_start', 'monday_end',
            'tuesday_start', 'tuesday_end',
            'wednesday_start', 'wednesday_end',
            'thursday_start', 'thursday_end',
            'friday_start', 'friday_end',
            'saturday_start', 'saturday_end',
            'sunday_start', 'sunday_end',
        ]
        widgets = {
            'monday_start': forms.TimeInput(format='%H:%M', attrs={'type': 'time'}),
            'monday_end': forms.TimeInput(format='%H:%M', attrs={'type': 'time'}),
            'tuesday_start': forms.TimeInput(format='%H:%M', attrs={'type': 'time'}),
            'tuesday_end': forms.TimeInput(format='%H:%M', attrs={'type': 'time'}),
            'wednesday_start': forms.TimeInput(format='%H:%M', attrs={'type': 'time'}),
            'wednesday_end': forms.TimeInput(format='%H:%M', attrs={'type': 'time'}),
            'thursday_start': forms.TimeInput(format='%H:%M', attrs={'type': 'time'}),
            'thursday_end': forms.TimeInput(format='%H:%M', attrs={'type': 'time'}),
            'friday_start': forms.TimeInput(format='%H:%M', attrs={'type': 'time'}),
            'friday_end': forms.TimeInput(format='%H:%M', attrs={'type': 'time'}),
            'saturday_start': forms.TimeInput(format='%H:%M', attrs={'type': 'time'}),
            'saturday_end': forms.TimeInput(format='%H:%M', attrs={'type': 'time'}),
            'sunday_start': forms.TimeInput(format='%H:%M', attrs={'type': 'time'}),
            'sunday_end': forms.TimeInput(format='%H:%M', attrs={'type': 'time'}),
        }


class EmployeeRequirementForm(forms.ModelForm):
    class Meta:
        model = EmployeeRequirement
        fields = ['day_of_week']

class ShiftForm(forms.ModelForm):
    class Meta:
        model = Shift
        fields = ['start_time', 'end_time']
        widgets = {
            'start_time': forms.TimeInput(attrs={'type': 'time'}),
            'end_time': forms.TimeInput(attrs={'type': 'time'}),
        }

ShiftFormSet = inlineformset_factory(EmployeeRequirement, Shift, form=ShiftForm, extra=1)

class ShiftRequirementForm(forms.ModelForm):
    class Meta:
        model = ShiftRequirement
        fields = ['day_of_week', 'start_time', 'end_time', 'required_employees']

ShiftRequirementFormSet = inlineformset_factory(ServiceConstraints, ShiftRequirement, form=ShiftRequirementForm, extra=1)

class WeekSelectionForm(forms.Form):
    start_date = forms.DateField(
        label='Date de début de la semaine',
        widget=forms.DateInput(attrs={'type': 'date'}),
        initial=timezone.now().date()
    )
    hours_per_week = forms.IntegerField(
        label='Heures par semaine (optionnel)',
        required=False,
        min_value=1,
        max_value=168
    )

class LeaveRequestForm(forms.ModelForm):
    REASON_CHOICES = [
        ('conge_paye', 'Congé payé'),
        ('arret_maladie', 'Arrêt maladie'),
        ('indisponible', 'Indisponibilité'),
        # Ajoutez d'autres options si nécessaire
    ]
    reason = forms.ChoiceField(choices=REASON_CHOICES)
    comments = forms.CharField(widget=forms.Textarea, required=False, label="Commentaires")

    class Meta:
        model = LeaveRequest
        fields = ['start_date', 'end_date', 'reason']
        widgets = {
            'start_date': forms.DateInput(attrs={'type': 'date'}),
            'end_date': forms.DateInput(attrs={'type': 'date'}),
            'reason': forms.Textarea(attrs={'rows': 3})
        }    

class UpdateLeaveRequestForm(forms.ModelForm):
    start_date = forms.DateField(widget=forms.DateInput(attrs={'type': 'date'}))
    end_date = forms.DateField(widget=forms.DateInput(attrs={'type': 'date'}))

    class Meta:
        model = LeaveRequest
        fields = ['start_date', 'end_date', 'reason']

class UserProfileForm(forms.ModelForm):
    class Meta:
        model = CustomUser
        fields = ['first_name', 'last_name', 'email', 'photo']  # Ajustez les champs selon vos besoins