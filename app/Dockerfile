FROM python:3.12-slim

# Utilisateur non-root : bonne pratique de sécurité (durcissement).
# Si l'appli est compromise, l'attaquant n'a pas les droits root du conteneur.
RUN groupadd -r socket && useradd -r -g socket socket

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

RUN chown -R socket:socket /app
USER socket

EXPOSE 5000

CMD ["python", "app.py"]