Prérequis

Avant de lancer le projet, assurez-vous d'avoir installé les éléments suivants :

Python 3.7 ou supérieur
Django 3.2 ou supérieur
Git

Installation

Cloner le dépôt :   

git clone https://github.com/Mohamedzahirr/TER.git
cd  .\automatisationPlan\


Créer un environnement virtuel :


python -m venv venv

Activer l'environnement virtuel :
Sur Windows :

venv\Scripts\activate

Sur macOS et Linux :

source venv/bin/activate




Appliquer les migrations :

python manage.py migrate

Lancer le serveur de développement :

python manage.py runserver

Accéder à l'application :

Ouvrez votre navigateur et allez à l'adresse suivante :

http://127.0.0.1:8000/


Utilisation
Connectez-vous en tant qu'administrateur pour gérer les employés, générer des plannings, et suivre les heures de pointage.
