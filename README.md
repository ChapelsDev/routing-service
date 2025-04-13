
```markdown
# Routing Service

This project sets up a routing service with Flask. The instructions below cover how to create a virtual environment, manage dependencies, control the database, and run the application both directly and inside a Docker container.

### Dependencies

- **Docker**  
  [https://www.docker.com/](https://www.docker.com/)

- **Python**  
  [https://www.python.org/](https://www.python.org/)

## Virtual Environment Setup

### 1. Create or Recreate the Virtual Environment

```bash
python -m venv .venv
```

### 2. Activate the Virtual Environment

- **Windows (PowerShell):**
  ```powershell
  .\.venv\Scripts\Activate
  ```

- **Windows (CMD):**
  ```cmd
  .\.venv\Scripts\activate.bat
  ```

- **Linux:**
  ```bash
  source .venv/bin/activate
  ```

## Installing and Updating Dependencies

### Install Dependencies

Install the required dependencies from the `requirements.txt` file:

```bash
pip install -r requirements.txt
```

### Update Requirements

After making changes to your environment, regenerate the `requirements.txt` file with:

```bash
pip freeze > requirements.txt
```

## Database Management

### Delete the Database

*Note:* The command below is used because the database should not be deleted manually from its location.

```bash
python manage.py delete
```

### Recreate Tables

To create (or recreate) the database tables, run:

```bash
python manage.py recreate
```

## Running the Flask Server

### Directly via Flask

1. Navigate to the `src` folder:
   ```bash
   cd src
   ```
2. Start the Flask server:
   ```bash
   python main.py
   ```

## Docker Container Setup

### Build the Docker Image

Build the Docker image with the tag `routing-service`:

```bash
docker build -t routing-service .
```

### Running the Docker Container

To run the container and map port 5000 from the container to your host—while using a Docker named volume for your SQLite database—use the following command:

```bash
docker run -p 5000:5000 -v routing_data:/app/data routing-service
```

**Explanation:**

- `-p 5000:5000`: Maps port 5000 in the container to port 5000 on the host.
- `-v routing_data:/app/data`: Uses a Docker named volume called `routing_data` to persist files under `/app/data` (where your Flask application is configured to create `routes.db`). Docker automatically creates this volume if it doesn't exist, so the user doesn't need to manually create any directories.

## Flask App Configuration Note

Ensure your Flask configuration (in your main file, e.g., `src/main.py`) points to the correct SQLite database location:

```python
app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:////app/data/routes.db"
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
```
