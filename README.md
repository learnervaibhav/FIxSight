# FixSight - Agentic AI Predictive Maintenance System

An intelligent automotive aftersales predictive maintenance system powered by multi-agent AI orchestration.

[Important Note: The project is in development.]

[Presentation and prototype video link: https://drive.google.com/drive/folders/1T6Qv0jvBJCoti56geanMWlV-3ux74rvc?usp=sharing]

## 🎯 Overview

FixSight uses autonomous AI agents to predict vehicle failures, engage customers proactively, schedule services automatically, and provide manufacturing feedback - all while monitoring agent behavior for anomalies.

## 🏗️ Architecture

### Multi-Agent System
- **Master Agent**: Orchestrates the entire workflow
- **Data Analysis Agent**: Identifies anomalies in vehicle telemetry
- **Diagnosis Agent**: Predicts failures and severity
- **Customer Engagement Agent**: Communicates with customers persuasively
- **Scheduling Agent**: Books appointments automatically
- **Manufacturing Feedback Agent**: Generates RCA/CAPA insights

### Technology Stack
- **Backend**: Flask (Python)
- **Database**: SQLite
- **AI Framework**: LangGraph + CrewAI
- **LLM**: OpenAI GPT
- **Frontend**: HTML/CSS/JavaScript

## 🚀 Quick Start

### Prerequisites
- Python 3.9+
- OpenAI API Key

### Installation

1. Clone the repository
```bash
cd FixSight
```

2. Create virtual environment
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. Install dependencies
```bash
pip install -r requirements.txt
```

4. Configure environment
```bash
cp .env.example .env
# Edit .env and add your OPENAI_API_KEY
```

5. Initialize database
```bash
python scripts/init_database.py
```

6. Run the application
```bash
python app.py
```

7. Access the dashboard
```
http://localhost:5000
```

## 📁 Project Structure

```
FixSight/
├── app.py                      # Main Flask application
├── config.py                   # Configuration settings
├── requirements.txt            # Python dependencies
├── agents/                     # AI Agents
│   ├── master_agent.py        # Master orchestrator
│   ├── data_analysis_agent.py # Anomaly detection
│   ├── diagnosis_agent.py     # Failure prediction
│   ├── customer_agent.py      # Customer engagement
│   ├── scheduling_agent.py    # Appointment booking
│   └── manufacturing_agent.py # RCA/CAPA generation
├── models/                     # Database models
├── routes/                     # API endpoints
├── services/                   # Business logic
├── static/                     # Frontend assets
├── templates/                  # HTML templates
└── scripts/                    # Utility scripts
```

## 🎬 Demo Flow

1. **Data Ingestion**: Vehicle telemetry arrives (simulated)
2. **Anomaly Detection**: Data Analysis Agent flags issues
3. **Diagnosis**: Diagnosis Agent predicts failure
4. **Master Orchestration**: Master Agent coordinates response
5. **Customer Engagement**: Customer Agent creates persuasive message
6. **Scheduling**: Scheduling Agent books appointment
7. **Manufacturing Feedback**: RCA/CAPA report generated
8. **UEBA**: All agent actions logged and monitored

## 🔑 Key Features

- Predictive maintenance with AI
- Proactive customer engagement
- Intelligent scheduling
- Manufacturing feedback loop (RCA/CAPA)
- UEBA for agent behavior monitoring

## 📊 API Endpoints

- `POST /api/telemetry/ingest` - Ingest vehicle data
- `POST /api/predict` - Trigger prediction workflow
- `POST /api/schedule` - Book service appointment
- `GET /api/dashboard/status` - System status

## 🧪 Testing

Run demo scenario:
```bash
python scripts/demo_scenario.py
```

## 📝 License

MIT License
