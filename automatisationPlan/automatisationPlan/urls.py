"""
URL configuration for automatisationPlan project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.0/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path
from django.conf import settings
from django.conf.urls.static import static

from django.contrib.auth import views as auth_views
from accounts.views import CancelLeaveRequestView, DeleteEmployeeView, DeleteTeamLeadView, DeleteTimeClockView, EditTimeClockView, EmployeeHoursDetailView, EmployeeRequirementCreateView, EmployeeRequirementDeleteView, EmployeeRequirementListView, EmployeeRequirementUpdateView, GenerateScheduleView, LeaveRequestListView, ManagerEmployeeHoursView, ManagerLeaveRequestsView, NotificationListView, PointageView, ServiceConstraintsCreateView, ServiceConstraintsListView, ServiceConstraintsUpdateView, SignUpView, LoginView, TeamLeadPointageView, UpdateLeaveRequestStatusView, UpdateLeaveRequestView, UpdateScheduleView, ViewScheduleView, WorkHoursDetailView, WorkHoursView, add_shift, download_schedule_pdf, home, ManagerCreateUserView, EmployeeListView, TeamLeadListView, EmployeeUpdateView, TeamLeadUpdateView, LogoutView, SubmitLeaveRequestView, modify_shift, send_schedule_notifications
from accounts.views import AvailabilityCreateView, AvailabilityUpdateView, AvailabilityDeleteView, AvailabilityListView, profile_view , logout_confirmation_view
urlpatterns = [
    path('admin/', admin.site.urls),
    path('', home, name='home'),
    path('signup/', SignUpView.as_view(), name='signup'),
    path('login/', LoginView.as_view(), name='login'),
    path('profile/', profile_view, name='profile'),
    path('create_user/', ManagerCreateUserView.as_view(), name='create_user'),
    path('employees/', EmployeeListView.as_view(), name='employee_list'),
    path('employees/edit/<int:pk>/', EmployeeUpdateView.as_view(), name='edit_employee'),
    path('team_leads/', TeamLeadListView.as_view(), name='team_lead_list'),
    path('team_leads/edit/<int:pk>/', TeamLeadUpdateView.as_view(), name='edit_team_lead'),
    path('logout/', LogoutView.as_view(), name='logout'),
    path('logout/confirmation/', logout_confirmation_view, name='logout_confirmation'),
    path('availabilities/add/<int:pk>/', AvailabilityCreateView.as_view(), name='add_availability'),
    path('availabilities/edit/<int:pk>/', AvailabilityUpdateView.as_view(), name='edit_availability'),
    path('availabilities/delete/<int:pk>/', AvailabilityDeleteView.as_view(), name='delete_availability'),
    path('availabilities/view/<int:pk>/', AvailabilityListView.as_view(), name='view_availabilities'),
    path('constraints/', ServiceConstraintsListView.as_view(), name='constraints_list'),
    path('constraints/add/', ServiceConstraintsCreateView.as_view(), name='add_constraint'),
    path('constraints/edit/<int:pk>/<str:day>/', ServiceConstraintsUpdateView.as_view(), name='edit_constraint_day'),
    path('employee_requirements/', EmployeeRequirementListView.as_view(), name='manage_employee_requirements'),
    path('employee_requirements/add/', EmployeeRequirementCreateView.as_view(), name='add_employee_requirement'),
    path('employee_requirements/edit/<int:pk>/', EmployeeRequirementUpdateView.as_view(), name='edit_employee_requirement'),
    path('employee_requirements/delete/<int:pk>/', EmployeeRequirementDeleteView.as_view(), name='delete_employee_requirement'),


    path('generate_schedule/', GenerateScheduleView.as_view(), name='generate_schedule'),
    path('view_schedule/', ViewScheduleView.as_view(), name='view_schedule'),
    path('leave_request/submit/', SubmitLeaveRequestView.as_view(), name='submit_leave_request'),
    path('leave_request/list/', LeaveRequestListView.as_view(), name='leave_request_list'),
    path('leave_request/update/<int:pk>/', UpdateLeaveRequestView.as_view(), name='update_leave_request'),
    path('leave_request/cancel/<int:pk>/', CancelLeaveRequestView.as_view(), name='cancel_leave_request'),
  
    path('manager_leave_requests/', ManagerLeaveRequestsView.as_view(), name='manager_leave_requests'),
    path('leave_request/update_status/<int:pk>/', UpdateLeaveRequestStatusView.as_view(), name='update_leave_request_status'),
    path('notifications/', NotificationListView.as_view(), name='notification_list'),
    path('pointage /', PointageView.as_view(), name='pointage'),
    path('team_lead_pointage/', TeamLeadPointageView.as_view(), name='team_lead_pointage'),
    path('work_hours/', WorkHoursView.as_view(), name='work_hours'),
    path('work_hours/detail/', WorkHoursDetailView.as_view(), name='work_hours_detail'),
    path('download_schedule_pdf/', download_schedule_pdf, name='download_schedule_pdf'),
    path('modify_shift/', modify_shift, name='modify_shift'),
    path('modify_shift/<int:employee_id>/<str:day>/', modify_shift, name='modify_shift'),
    path('add_shift/<int:employee_id>/<str:day>/', add_shift, name='add_shift'),
    path('update_schedule/', UpdateScheduleView.as_view(), name='update_schedule'),

    path('delete_employee/<int:pk>/', DeleteEmployeeView.as_view(), name='delete_employee'),
    path('delete_team_lead/<int:pk>/', DeleteTeamLeadView.as_view(), name='delete_team_lead'),
    path('manager/employee-hours/', ManagerEmployeeHoursView.as_view(), name='manager_employee_hours'),
    path('edit_timeclock/<int:clock_in_id>/', EditTimeClockView.as_view(), name='edit_timeclock'),
    path('delete_timeclock/<int:clock_in_id>/', DeleteTimeClockView.as_view(), name='delete_timeclock'),
    path('send_schedule_notifications/', send_schedule_notifications, name='send_schedule_notifications'),
    path('employee/<int:employee_id>/hours/<int:year>/<int:month>/', EmployeeHoursDetailView.as_view(), name='employee_hours_detail'),





] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)