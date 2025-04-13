
---

```markdown
# Routing Service

This project sets up a routing service with Flask. The instructions below cover how to create a virtual environment, manage dependencies, control the database, and run the application both directly and inside a Docker container.

### Dependencies

- **DOCKER**
    ```
    https://www.docker.com/
    ```
- **Pyhton**
    ```
    https://www.python.org/

    ```

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
When you update your environment, you can regenerate the `requirements.txt` file by running:

```bash
pip freeze > requirements.txt
```

## Database Management

### Exclude/Delete the Database
*Note:* The command below is used because the database in `/instances/routes.db` should not be deleted manually.
  
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
To run the container and map port 5000 from the container to your host:

```bash
docker run -p 5000:5000 -v routing_data:/app/data routing-service
```

---