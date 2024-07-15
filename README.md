# Setup

1. Install [Python](https://www.python.org/downloads/), [Git](https://git-scm.com/downloads), and [ODBC Driver](https://learn.microsoft.com/en-us/sql/connect/odbc/download-odbc-driver-for-sql-server?view=sql-server-ver16#version-17).
2. Create a new directory and clone this repo into it.
```
git clone https://github.com/FelidaeFundConservation/WildeBackyardBackend.git
```
3. Open a command terminal and create/activate a virtual environment.
```
python -m venv /path/to/new/virtual/environment
```
4. Navigate to the wildebackyard directory. Install dependencies with pip within the venv.
```
pip install -r requirements.txt
```

5. Fix package migration files by following the below steps.

---
## django-rest-passwordreset Package Fix

This project uses the django-rest-passwordreset package.
https://pypi.org/project/django-rest-passwordreset/

However, there is an issue with the token model that causes a NOT NULL constraint error. 

### As a current workaround, the the "id" field needs to be removed from the model and migrations for this package.

1. Navigate to the installed package, such as wildebackyard\venv\Lib\site-packages\django_rest_passwordreset.
2. Delete the "id" AutoField in the ResetPasswordToken model.
3. Delete all migration files within the passwordreset package.
4. Remake migrations.

```
python manage.py makemigrations
```

The migrations should now be consistent with the database, and should work locally for development.

---
## Test Run Server

Try running the server to see if it works. 
```
python manage.py runserver --settings=config.settings.local
```

To connect to staging or even prod databases, replace "local" with "staging" or "prod."

<i>(!) Please be careful when working with data while connected to prod, as this is live data.</i>

---
## Developing A Feature
1. Self-assign or request to be assigned an issue.
2. Make sure your local repo is up to date.
   
```
git checkout main
git pull origin main
```

3. Create a new feature branch with a name which accurately captures the intent. (ex. add_comments_section)

```
git checkout -b <BRANCH_NAME>
```

4. Implement your feature, fix, etc.
5. When done working on the feature, push your local branch to the repo.
   
```
git push origin <BRANCH_NAME>
```

6. Open a Pull Request, add a reviewer, and link the issue to the PR.
7. After the code is reviewed, merge the branch into main.

<i>Your feature is now integrated!</i>

---
## Deployment Info
This repository is connected to Azure CI/CD. Any pushes/merges into the "staging" or "prod" branches will deploy the code to App Service automatically to the respective environment. 
