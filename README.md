# Cerebro - Integrated Management System

Cerebro is a comprehensive, Django-based web application designed to serve as the central hub for an organization's internal management processes. It provides an integrated suite of tools for Quality Management (QMS), corrective/preventive action plans, and innovation management, turning complex operational requirements into a streamlined, auditable, and collaborative digital workflow.

## Core Features

The application is built on a modular architecture, with each module handling a specific business function:

### 1. 📄 Document Management (`docs` app)
The heart of the Quality Management System (QMS), this module provides a centralized and version-controlled repository for all official company documents.
- **Structured Library:** Documents are organized by process and type, creating a logical and easily searchable knowledge base.
- **Version Control:** A full revision history is maintained for every document. When a file is updated, a new `Revision` is created, logging the changes and linking to the new file, ensuring full traceability.
- **Feedback Loop:** A "Report" feature allows users to flag issues with documents (e.g., errors, outdated content), creating a ticket for review and ensuring the QMS remains accurate and reliable.

### 2. 📈 Action Plan Tracking (`pas` app)
This module provides a formal system for managing, tracking, and documenting corrective and preventive action plans.
- **Formal Plans:** Create detailed action plans, such as a "Cédula de No Conformidad" (CNC) or a "Plan de Cambios y Mejoras" (PCM).
- **Task Delegation:** Break down high-level plans into specific, actionable tasks (`Accion`), each with an assigned responsible party and due dates.
- **Progress Monitoring:** Track the status of each action with detailed `Seguimiento` (follow-up) entries, creating a complete audit trail from problem identification to resolution.

### 3.💡 Idea & Innovation Management (`ideas` app)
This module serves as a digital suggestion box, empowering employees to contribute to the organization's growth and improvement.
- **Idea Submission:** Users can submit proposals, from simple ideas to fully-fledged projects, including descriptions, supporting documents, and evidence.
- **Formal Review:** A `Resolve` system ensures that every submission is formally reviewed by management. The outcome (e.g., Viable, Not Viable, On Hold) is documented and communicated.
- **Fosters Culture:** Encourages a bottom-up approach to innovation and makes employees active participants in the company's evolution.

### 4. 👤 User & Profile Management (`profiles` app)
This module extends Django's built-in authentication system to map the organization's structure directly into the application.
- **Custom Profiles:** Each user has a profile detailing their specific role, position, and site (e.g., "Vocal del RFE de Junta Local").
- **Contextual Permissions:** Provides the foundation for role-based access control, ensuring users can only see and do what is relevant to their position.

## Technical Architecture

- **Backend:** Django
- **Database:** PostgreSQL
- **Frontend:** Django Templates with `django-crispy-forms` and Bootstrap.
- **Deployment:** The project is configured for production deployment using Nginx (as a reverse proxy) and Supervisor (for process management). Docker and Vagrant files are also included for containerized or virtualized environments.

## Getting Started

Follow these instructions to set up a local development environment.

### Prerequisites

- Python 3.x
- Pip
- PostgreSQL server

### 1. Installation

First, clone the repository and navigate into the project directory:
```bash
git clone <your-repo-url>
cd cerebro
```

Next, it is highly recommended to create and activate a Python virtual environment:
```bash
python -m venv venv
source venv/bin/activate  # On Windows use `venv\Scripts\activate`
```

Install the required Python packages using `pip`:
```bash
pip install -r requirements.txt
```

### 2. Configuration

The application uses a `.env` file for environment-specific configuration. Create a file named `.env` inside the `src/` directory (`src/.env`).

Copy the following template into your `src/.env` file and fill in the values for your local environment.

```env
# --- General Settings ---
# Set to True for development to get detailed error pages. MUST be False in production.
DEBUG=True

# Set to True if your development server uses HTTPS.
SSL=False

# --- Database Settings ---
# Connection string for your PostgreSQL database.
# Format: postgresql://<USER>:<PASSWORD>@<HOST>:<PORT>/<DB_NAME>
DATABASE_URL=postgresql://cerebro_user:your_password@localhost:5432/cerebro_db

# --- Email Settings (Optional for local development) ---
# Used for sending emails (e.g., password resets, notifications).
EMAIL_HOST=
EMAIL_PORT=587
EMAIL_HOST_USER=
EMAIL_HOST_PASSWORD=
```

### 3. Database Setup

Before running the application, you need to prepare the PostgreSQL database.

First, create the database and a user with the credentials you specified in your `.env` file. Then, configure the user's default settings by running the following SQL commands:

```sql
ALTER ROLE your_db_user SET client_encoding TO 'utf8';
ALTER ROLE your_db_user SET default_transaction_isolation TO 'read committed';
ALTER ROLE your_db_user SET timezone TO 'Mexico/General';
```

Once the database is ready, run the Django migrations to create the application's tables:
```bash
python src/manage.py migrate
```

### 4. Running the Development Server

You can now start the local development server:
```bash
python src/manage.py runserver
```

The application will be available at `http://127.0.0.1:8000`.

## Project Structure

```
cerebro/
├── conf/              # Deployment configuration (Nginx, Supervisor).
├── src/
│   ├── .env           # (You create this) Environment variables.
│   ├── manage.py      # Django's command-line utility.
│   ├── apps/          # Contains the core Django applications (modules).
│   │   ├── docs/
│   │   ├── ideas/
│   │   ├── pas/
│   │   └── profiles/
│   └── core/          # Core project package (settings, main URLs).
├── requirements.txt   # Python dependencies.
├── Dockerfile         # For building a Docker image.
└── README.md          # This file.
```