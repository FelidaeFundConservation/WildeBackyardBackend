# Setup

Install ODBC Driver at:
https://learn.microsoft.com/en-us/sql/connect/odbc/download-odbc-driver-for-sql-server?view=sql-server-ver16#version-17

---

This project uses the django-rest-passwordreset package.
https://pypi.org/project/django-rest-passwordreset/

However, there is an issue with the token model that causes a NOT NULL constraint error. 
As a current workaround, the model and migrations need to remove the "id" field.

Example: 
- Navigate to the installed package, such as wildebackyard\venv\Lib\site-packages\django_rest_passwordreset.
- Delete the "id" AutoField in the ResetPasswordToken model.
- Delete all migration files.
- Remake migrations.

The migrations should now be consistent with the database.
