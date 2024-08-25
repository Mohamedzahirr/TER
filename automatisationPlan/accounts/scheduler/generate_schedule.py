from ortools.sat.python import cp_model
from datetime import datetime, timedelta
import random

def time_difference_in_minutes(start, end):
    start_dt = datetime.combine(datetime.min, start)
    end_dt = datetime.combine(datetime.min, end)
    if end_dt < start_dt:
        end_dt += timedelta(days=1)
    return int((end_dt - start_dt).total_seconds() / 60)

def generate_schedule(employees, availabilities, constraints, start_date, end_date):
    print("Debug: Starting generate_schedule function")
    print(f"Debug: Number of employees: {len(employees)}")
    print(f"Debug: Number of availabilities: {len(availabilities)}")
    print(f"Debug: Constraints keys: {constraints.keys()}")
    
    print("Début de la création des variables de shift")


    detailed_messages = []
    
    # Vérifier les disponibilités des employés
    available_employees = [e for e in employees if availabilities.get(e.id)]
    max_required = max(sum(day_req) for day_req in constraints['required_employees'])
    if len(available_employees) < max_required:
        detailed_messages.append(f"Il n'y a pas assez d'employés disponibles. Vous avez besoin d'au moins {max_required} employés disponibles.")

    # Vérifier les chefs d'équipe
    team_leads = [e for e in employees if getattr(e, 'role', '') == 'team_lead' and availabilities.get(e.id)]
    if not team_leads:
        detailed_messages.append("Aucun chef d'équipe n'est disponible. Assurez-vous qu'au moins un chef d'équipe a des disponibilités.")

    # Vérifier les exigences de shifts
    for day_index, (day, shifts) in enumerate(constraints['shifts']):
        required = sum(constraints['required_employees'][day_index])
        available = sum(1 for e in employees if any(a.day_of_week == day for a in availabilities.get(e.id, [])))
        if available < required:
            detailed_messages.append(f"Il n'y a pas assez d'employés disponibles le {day}. Requis : {required}, Disponibles : {available}")

    
    model = cp_model.CpModel()
    shifts = {}
    days_of_week = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
    detailed_messages = []

    # Create shift variables
    shifts = {}
    for employee in employees:
        print(f"Debug: Processing employee {employee.id}")
        for day_index, day_data in enumerate(constraints['shifts']):
            day, day_shifts = day_data
            print(f"Debug: Processing day {day}")
            for shift_index, (start, end) in enumerate(day_shifts):
                shift = model.NewBoolVar(f'shift_{employee.id}_{day}_{shift_index}')
                shifts[(employee.id, day, shift_index)] = shift
                if employee.id not in availabilities:
                    print(f"Debug: No availabilities for employee {employee.id}")
                    detailed_messages.append(f"L'employé {employee.first_name} {employee.last_name} n'a aucune disponibilité définie.")
                    continue
                if not any(a.day_of_week == day and a.start_time <= start and a.end_time >= end for a in availabilities[employee.id]):
                    model.Add(shift == 0)

    print("Debug: Shifts keys:", list(shifts.keys()))
    # Ensure required number of employees per shift with relaxation
    shift_slacks = {}
    for day_index, day_data in enumerate(constraints['shifts']):
        day, day_shifts = day_data
        for shift_index, (start, end) in enumerate(day_shifts):
            required = constraints['required_employees'][day_index][shift_index]
            slack = model.NewIntVar(0, len(employees), f'slack_{day}_{shift_index}')
            shift_slacks[(day, shift_index)] = slack
            model.Add(sum(shifts.get((e.id, day, shift_index), 0) for e in employees) + slack >= int(required))


    # Max minutes per day constraint with relaxation
    day_slacks = {}
    # Max minutes per day constraint with fixed 12-hour limit
    max_minutes_per_day = 12 * 60  # 12 hours in minutes
    for employee in employees:
        for day_index, day_data in enumerate(constraints['shifts']):
            day, day_shifts = day_data
            total_minutes = sum(
                time_difference_in_minutes(start, end) * shifts.get((employee.id, day, shift_index), 0)
                for shift_index, (start, end) in enumerate(day_shifts)
            )
            model.Add(total_minutes <= max_minutes_per_day)

    # Max minutes per week constraint (with 5 hour flexibility, only for upper bound)
    for employee in employees:
        if not hasattr(employee, 'hours_per_week'):
            print(f"Debug: Employee {employee.id} does not have 'hours_per_week' attribute")
            detailed_messages.append(f"Les heures de travail par semaine ne sont pas définies pour {employee.first_name} {employee.last_name}.")
            continue
        max_weekly_minutes = int(employee.hours_per_week * 60)
        weekly_minutes = sum(
            time_difference_in_minutes(start, end) * shifts.get((employee.id, day, shift_index), 0)
            for day_data in constraints['shifts']
            for day, day_shifts in [day_data]
            for shift_index, (start, end) in enumerate(day_shifts)
    )
        # Remove the lower bound constraint
        # model.Add(weekly_minutes >= max_weekly_minutes - 300)
        # Keep only the upper bound constraint
        model.Add(weekly_minutes <= max_weekly_minutes + 300)



    for day_index, day_data in enumerate(constraints['shifts']):
        day, day_shifts = day_data
        for shift_index, (start, end) in enumerate(day_shifts):
            required = constraints['required_employees'][day_index][shift_index]
            model.Add(sum(shifts.get((e.id, day, shift_index), 0) for e in employees) == required)


    # Consecutive rest days constraint with relaxation
    print("Début de l'ajout des contraintes de jours de repos")
    min_consecutive_rest_days = int(constraints['min_consecutive_rest_days'])
    rest_slacks = {}
    for employee in employees:
        print(f"Ajout de la contrainte de jours de repos pour l'employé {employee.id}")
        for start_day in range(7 - min_consecutive_rest_days + 1):
            slack = model.NewIntVar(0, min_consecutive_rest_days, f'slack_rest_{employee.id}_{start_day}')
            rest_slacks[(employee.id, start_day)] = slack
            rest_days = [
                model.NewBoolVar(f'rest_day_{employee.id}_{day}')
                for day in range(start_day, start_day + min_consecutive_rest_days)
            ]
            for day, rest_day in enumerate(rest_days, start=start_day):
                day_name = days_of_week[day % 7]
                day_shifts = constraints['shifts'][day % 7][1]
                model.Add(sum(shifts[(employee.id, day_name, shift_index)] 
                            for shift_index in range(len(day_shifts))) == 0).OnlyEnforceIf(rest_day)
            model.Add(sum(rest_days) + slack >= min_consecutive_rest_days)
    print("Fin de l'ajout des contraintes de jours de repos")

# Objective: Minimize all slack variables
# Objective: Minimize all slack variables
    model.Minimize(
        sum(slack for slack in shift_slacks.values()) +
        sum(slack for slack in day_slacks.values()) +
        sum(slack for slack in rest_slacks.values())
    )
    # Solve the model
    solver = cp_model.CpSolver()
    solver.parameters.max_time_in_seconds = 300.0  # 5 minutes
    solver.parameters.log_search_progress = True
    status = solver.Solve(model)


    if status == cp_model.INFEASIBLE:
        detailed_messages.append("Le problème est infaisable. Voici les détails :")
        detailed_messages.append(f"Nombre d'employés : {len(employees)}")
        detailed_messages.append(f"Nombre de jours : {len(constraints['shifts'])}")
        
        # Ajoutez ces informations essentielles
        detailed_messages.append("Contraintes spécifiques :")
        detailed_messages.append("La 19ème contrainte linéaire est impossible à satisfaire. (Cette contrainte pourrait être liée au nombre minimum d'heures de travail par semaine ou au nombre maximum d'heures de travail par jour pour un employé.)")
        detailed_messages.append("Cela peut être dû à un conflit entre le nombre d'employés requis et leurs disponibilités.")
        
        # Information sur l'employé avec disponibilité limitée
        limited_availability_employee = next((e for e in employees if len(availabilities[e.id]) < 7), None)
        if limited_availability_employee:
            detailed_messages.append(f"L'employé {limited_availability_employee.first_name} {limited_availability_employee.last_name} (ID: {limited_availability_employee.id}) n'est disponible que {len(availabilities[limited_availability_employee.id])} jours sur 7.")

        detailed_messages.append("Suggestions :")
        detailed_messages.append("1. Vérifiez si vous pouvez réduire le nombre d'employés requis par shift.")
        detailed_messages.append("2. Assurez-vous que tous les employés ont suffisamment de disponibilités.")
        detailed_messages.append("3. Considérez d'ajouter plus de flexibilité dans les horaires des shifts.")

        return None, detailed_messages

    elif status == cp_model.OPTIMAL or status == cp_model.FEASIBLE:
        schedule = []
        day_name_mapping = {
            'Monday': 'Lundi', 'Tuesday': 'Mardi', 'Wednesday': 'Mercredi',
            'Thursday': 'Jeudi', 'Friday': 'Vendredi', 'Saturday': 'Samedi', 'Sunday': 'Dimanche'
        }
            
        for (e_id, day, shift_index), shift in shifts.items():
            if solver.Value(shift):
                employee = next((e for e in employees if e.id == e_id), None)
                if employee is None:
                    print(f"Debug: Employee with id {e_id} not found")
                    continue
                start, end = constraints['shifts'][days_of_week.index(day)][1][shift_index]
                start_time = start.strftime("%H:%M")
                end_time = end.strftime("%H:%M")
                hours = time_difference_in_minutes(start, end) / 60
                day_index = days_of_week.index(day)
                date_of_day = start_date + timedelta(days=day_index)
                day_french = day_name_mapping.get(day, day)
                schedule.append({
                    'employee': employee,
                    'day': day_french,
                    'date': date_of_day.strftime('%Y-%m-%d'),
                    'start_time': start_time,
                    'end_time': end_time,
                    'hours': round(hours, 2)
                })
        print("Schedule generated successfully.")
        return schedule, detailed_messages

    else:
        print(f"Solver status: {solver.StatusName(status)}")
        return None, [f"Statut du solveur : {solver.StatusName(status)}"]
        

        