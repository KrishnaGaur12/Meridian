"""
RAZORPAY AI RISK MANAGER — Application Entry Point.
Provides FastAPI REST API application (`app`) & CLI interface.
Supports `uvicorn main:app --reload` as well as direct CLI execution.
"""

import sys
import argparse
import json
from pathlib import Path
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException

# Add project root to sys.path
BASE_DIR = Path(__file__).resolve().parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from src.database.database import init_db
from src.api.router import api_router
from src.pipeline.risk_engine import RiskEngine
from src.utils.data_generator import generate_scenario_files
from config.settings import SYNTHETIC_DATA_DIR, format_pct


# Initialize Database on Application Startup
@asynccontextmanager
async def lifespan(app_instance: FastAPI):
    init_db()
    yield


# FastAPI Application Definition
app = FastAPI(
    title="RAZORPAY AI RISK MANAGER & Evidence Engine API",
    description="Backend API for fraud risk prediction, chargeback evidence retrieval, and dispute management.",
    version="2.0.0",
    lifespan=lifespan
)


# ============================================================
# CORS CONFIGURATION
# Allows the RiskDesk frontend to communicate with this API.
# ============================================================

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


from sqlalchemy.exc import SQLAlchemyError

# ============================================================
# CUSTOM ERROR HANDLERS
# Prevent stack trace exposure to API clients.
# ============================================================

@app.exception_handler(StarletteHTTPException)
async def http_exception_handler(request: Request, exc: StarletteHTTPException):
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "detail": exc.detail,
            "error_code": f"HTTP_{exc.status_code}"
        }
    )


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(
    request: Request,
    exc: RequestValidationError
):
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={
            "detail": exc.errors(),
            "error_code": "VALIDATION_ERROR"
        }
    )


@app.exception_handler(SQLAlchemyError)
async def sqlalchemy_exception_handler(
    request: Request,
    exc: SQLAlchemyError
):
    return JSONResponse(
        status_code=status.HTTP_400_BAD_REQUEST,
        content={
            "detail": "A database operational error occurred.",
            "error_code": "DATABASE_ERROR"
        }
    )


@app.exception_handler(Exception)
async def unhandled_exception_handler(
    request: Request,
    exc: Exception
):
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "detail": "An internal server error occurred.",
            "error_code": "INTERNAL_SERVER_ERROR"
        }
    )


# ============================================================
# API ROUTER
# ============================================================

app.include_router(api_router)


# ============================================================
# CLI INTERFACE
# ============================================================

def render_cli_report(res: dict):
    """Prints formatted terminal report with consistent percentages."""

    comp_pct = format_pct(res['evidence_completeness'])
    fraud_pct = format_pct(res['fraud_probability'])
    win_pct = format_pct(res['win_probability'])
    conf_pct = format_pct(res['confidence'])

    print("\n========================================")
    print("        AI RISK MANAGER")
    print("========================================")

    print("\nDispute:")
    print(f"{res['dispute_id']}")

    print("\nReason:")
    print(f"{res['reason']}")

    print("\nEvidence Completeness:")
    print(f"{comp_pct}%")

    print("\nEvidence Quality:")
    print(f"{res['evidence_quality']}")

    print("\nContradictions:")
    print(f"{res['contradictions']}")

    if res['contradictions'] > 0:
        print(f"  Conflict Type : {res['contradiction_type']}")
        print(f"  Severity      : {res['contradiction_severity']}")
        print(f"  Evidence A    : {res['contradiction_evidence_a']}")
        print(f"  Evidence B    : {res['contradiction_evidence_b']}")

    print("\nFraud Probability:")
    print(f"{fraud_pct}%")

    print("\nFraud Risk:")
    print(f"{res['risk_level']}")

    print("\nWin Probability:")
    print(f"{win_pct}%")

    print("\nSystem Confidence:")
    print(f"{conf_pct}% ({res['confidence_level']})")

    print("\nRecommendation:")
    print(f"{res['recommendation']}")

    print("\nDecision Factors:")
    for reason in res.get('decision_reasons', []):
        print(f"  - {reason}")

    print("\nExplanation:")
    print(f"{res['explanation']}")

    print("========================================\n")


def main():
    parser = argparse.ArgumentParser(
        description="Razorpay AI Risk Manager — End-to-End Pipeline CLI"
    )

    parser.add_argument(
        "--dispute",
        type=str,
        help="Path to custom dispute JSON file"
    )

    parser.add_argument(
        "--scenario",
        type=int,
        choices=[1, 2, 3, 4, 5],
        help="Run one of 5 scenario files "
             "(1: CONTEST, 2: ACCEPT, 3: INVESTIGATE, "
             "4: FRAUD, 5: DUPLICATE)"
    )

    parser.add_argument(
        "--sample",
        action="store_true",
        help="Run analysis on default sample dispute"
    )

    parser.add_argument(
        "--ollama",
        action="store_true",
        help="Enable local Ollama LLM integration"
    )

    parser.add_argument(
        "--json",
        action="store_true",
        help="Output raw JSON response"
    )

    args = parser.parse_args()

    engine = RiskEngine(
        enable_ollama=args.ollama,
        use_vector_search=False
    )

    target_file = None

    if args.dispute:
        target_file = Path(args.dispute)

    elif args.scenario:
        scenario_map = {
            1: SYNTHETIC_DATA_DIR / "scenario_1_contest.json",
            2: SYNTHETIC_DATA_DIR / "scenario_2_accept.json",
            3: SYNTHETIC_DATA_DIR / "scenario_3_investigate.json",
            4: SYNTHETIC_DATA_DIR / "scenario_4_high_fraud.json",
            5: SYNTHETIC_DATA_DIR / "scenario_5_duplicate.json"
        }

        target_file = scenario_map.get(args.scenario)

        if not target_file.exists():
            generate_scenario_files()

    else:
        samples = list(
            SYNTHETIC_DATA_DIR.glob("scenario_*.json")
        )

        if not samples:
            generate_scenario_files()
            samples = list(
                SYNTHETIC_DATA_DIR.glob("scenario_*.json")
            )

        target_file = samples[0]

    if not target_file or not target_file.exists():
        print(
            f"Error: Target dispute file "
            f"'{target_file}' not found."
        )
        sys.exit(1)

    result = engine.analyze_dispute(target_file)

    if args.json:
        print(json.dumps(result, indent=2))
    else:
        render_cli_report(result)


if __name__ == "__main__":
    main()