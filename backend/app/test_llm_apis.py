"""
ORBIT-JR LLM API Diagnostic

File:
    backend/app/test_llm_apis.py

Run from project root:
    python backend/app/test_llm_apis.py

Reads configuration from:
    backend/.env
"""

from __future__ import annotations

import os
import sys
from pathlib import Path


# =========================================================
# 1. FIND PROJECT AND .ENV FILE
# =========================================================

CURRENT_FILE = Path(__file__).resolve()

# backend/app/test_llm_apis.py
# parents[0] = app
# parents[1] = backend
# parents[2] = orbit-jr
BACKEND_DIR = CURRENT_FILE.parents[1]
PROJECT_ROOT = CURRENT_FILE.parents[2]
ENV_FILE = BACKEND_DIR / ".env"


# =========================================================
# 2. LOAD DOTENV
# =========================================================

try:
    from dotenv import load_dotenv
except ModuleNotFoundError:
    print()
    print("=" * 70)
    print("ERROR")
    print("=" * 70)
    print("python-dotenv is not installed.")
    print()
    print("Run:")
    print("pip install python-dotenv")
    sys.exit(1)


load_dotenv(ENV_FILE)


# =========================================================
# 3. READ API CONFIGURATION
# =========================================================

OPENAI_API_KEY = os.getenv(
    "OPENAI_API_KEY",
    "",
).strip()

GEMINI_API_KEY = os.getenv(
    "GEMINI_API_KEY",
    "",
).strip()


OPENAI_MODEL = os.getenv(
    "OPENAI_MODEL",
    "gpt-5.6-luna",
).strip()


GEMINI_MODEL = os.getenv(
    "GEMINI_MODEL",
    "gemini-3.8-flash",
).strip()


# =========================================================
# 4. TEST RESULT STORAGE
# =========================================================

results = {
    "OpenAI Basic API": False,
    "OpenAI Web Search": False,
    "Gemini Basic API": False,
    "Gemini Google Search": False,
}


# =========================================================
# 5. HELPER FUNCTIONS
# =========================================================

def print_header(title: str) -> None:
    print()
    print("=" * 70)
    print(title)
    print("=" * 70)


def mask_key(key: str) -> str:

    if not key:
        return "MISSING"

    if len(key) <= 8:
        return "*" * len(key)

    return (
        key[:4]
        + "*" * (len(key) - 8)
        + key[-4:]
    )


def explain_error(
    provider: str,
    test_name: str,
    error: Exception,
) -> None:

    print()
    print(
        f"[FAILED] {provider} - {test_name}"
    )

    print(
        f"Error Type : {type(error).__name__}"
    )

    print(
        f"Error      : {error}"
    )

    status_code = getattr(
        error,
        "status_code",
        None,
    )

    if status_code is not None:
        print(
            f"Status Code: {status_code}"
        )

    error_code = getattr(
        error,
        "code",
        None,
    )

    if error_code is not None:
        print(
            f"Error Code : {error_code}"
        )

    print()
    print("Possible meaning:")

    message = str(error).lower()

    if (
        "401" in message
        or "unauthorized" in message
        or "invalid api key" in message
    ):
        print(
            "- API key is invalid, expired, "
            "or authentication failed."
        )

    elif (
        "403" in message
        or "forbidden" in message
        or "permission" in message
    ):
        print(
            "- API key does not have permission "
            "to use this model or tool."
        )

    elif (
        "429" in message
        or "quota" in message
        or "rate limit" in message
        or "resource exhausted" in message
    ):
        print(
            "- Rate limit, quota, or usage limit "
            "has been reached."
        )

    elif (
        "404" in message
        or "not found" in message
        or "model" in message
    ):
        print(
            "- The configured model may not exist "
            "or may not be available for your API account."
        )

    elif (
        "timeout" in message
        or "timed out" in message
        or "connection" in message
        or "network" in message
        or "dns" in message
    ):
        print(
            "- Network or internet connection problem."
        )

    elif (
        "web_search" in message
        or "google_search" in message
        or "search" in message
        and "tool" in message
    ):
        print(
            "- The basic API may be working, "
            "but the web-search tool failed."
        )

    else:
        print(
            "- Read the exact error printed above."
        )

    print()
    print(
        "The error above is the actual exception "
        "returned by the SDK/API."
    )


# =========================================================
# 6. CHECK PYTHON PACKAGES
# =========================================================

def check_packages() -> None:

    print_header(
        "STEP 1 - PACKAGE CHECK"
    )

    try:

        import openai

        version = getattr(
            openai,
            "__version__",
            "unknown",
        )

        print(
            f"OpenAI SDK       : INSTALLED ({version})"
        )

    except ModuleNotFoundError:

        print(
            "OpenAI SDK       : MISSING"
        )

        print(
            "Install with:"
        )

        print(
            "pip install openai"
        )


    try:

        import google.genai

        print(
            "Google GenAI SDK : INSTALLED"
        )

    except ModuleNotFoundError:

        print(
            "Google GenAI SDK : MISSING"
        )

        print(
            "Install with:"
        )

        print(
            "pip install google-genai"
        )


# =========================================================
# 7. CHECK .ENV
# =========================================================

def check_configuration() -> bool:

    print_header(
        "STEP 2 - .ENV CONFIGURATION"
    )

    print(
        f".env location:"
    )

    print(
        f"{ENV_FILE}"
    )

    print()

    print(
        f".env exists      : "
        f"{'YES' if ENV_FILE.exists() else 'NO'}"
    )

    print(
        f"OPENAI_API_KEY   : "
        f"{mask_key(OPENAI_API_KEY)}"
    )

    print(
        f"GEMINI_API_KEY   : "
        f"{mask_key(GEMINI_API_KEY)}"
    )

    print(
        f"OPENAI_MODEL     : "
        f"{OPENAI_MODEL}"
    )

    print(
        f"GEMINI_MODEL     : "
        f"{GEMINI_MODEL}"
    )

    if not OPENAI_API_KEY:

        print()
        print(
            "ERROR: OPENAI_API_KEY is missing."
        )

    if not GEMINI_API_KEY:

        print()
        print(
            "ERROR: GEMINI_API_KEY is missing."
        )

    return bool(
        OPENAI_API_KEY
        and GEMINI_API_KEY
    )


# =========================================================
# 8. OPENAI BASIC API TEST
# =========================================================

def test_openai_basic() -> bool:

    print_header(
        "STEP 3 - OPENAI BASIC API TEST"
    )

    if not OPENAI_API_KEY:

        print(
            "[SKIPPED] OPENAI_API_KEY is missing."
        )

        return False

    try:

        from openai import OpenAI

        client = OpenAI(
            api_key=OPENAI_API_KEY
        )

        response = client.responses.create(
            model=OPENAI_MODEL,
            input=(
                "Reply with exactly: "
                "ORBIT-JR OPENAI WORKING"
            ),
        )

        output = (
            response.output_text
            if response
            else ""
        )

        if not output:

            raise RuntimeError(
                "OpenAI returned an empty response."
            )

        print(
            "[SUCCESS] OpenAI basic API is working."
        )

        print()
        print(
            "Response:"
        )

        print(
            output.strip()
        )

        results[
            "OpenAI Basic API"
        ] = True

        return True

    except ModuleNotFoundError as error:

        explain_error(
            "OpenAI",
            "Basic API",
            error,
        )

        print(
            "Install:"
        )

        print(
            "pip install openai"
        )

        return False

    except Exception as error:

        explain_error(
            "OpenAI",
            "Basic API",
            error,
        )

        return False


# =========================================================
# 9. OPENAI WEB SEARCH TEST
# =========================================================

def test_openai_web_search() -> bool:

    print_header(
        "STEP 4 - OPENAI WEB SEARCH TEST"
    )

    if not OPENAI_API_KEY:

        print(
            "[SKIPPED] OPENAI_API_KEY is missing."
        )

        return False

    try:

        from openai import OpenAI

        client = OpenAI(
            api_key=OPENAI_API_KEY
        )

        response = client.responses.create(
            model=OPENAI_MODEL,

            tools=[
                {
                    "type": "web_search"
                }
            ],

            input=(
                "Use web search to find one current "
                "software developer job opening in India. "
                "Return only the company name, job title, "
                "and direct job URL."
            ),
        )

        output = (
            response.output_text
            if response
            else ""
        )

        if not output:

            raise RuntimeError(
                "OpenAI web search returned an empty response."
            )

        print(
            "[SUCCESS] OpenAI web search is working."
        )

        print()
        print(
            "Web Search Response:"
        )

        print(
            output.strip()
        )

        results[
            "OpenAI Web Search"
        ] = True

        return True

    except ModuleNotFoundError as error:

        explain_error(
            "OpenAI",
            "Web Search",
            error,
        )

        return False

    except Exception as error:

        explain_error(
            "OpenAI",
            "Web Search",
            error,
        )

        return False


# =========================================================
# 10. GEMINI BASIC API TEST
# =========================================================

def test_gemini_basic() -> bool:

    print_header(
        "STEP 5 - GEMINI BASIC API TEST"
    )

    if not GEMINI_API_KEY:

        print(
            "[SKIPPED] GEMINI_API_KEY is missing."
        )

        return False

    try:

        from google import genai

        client = genai.Client(
            api_key=GEMINI_API_KEY
        )

        interaction = client.interactions.create(
            model=GEMINI_MODEL,

            input=(
                "Reply with exactly: "
                "ORBIT-JR GEMINI WORKING"
            ),
        )

        output = (
            interaction.output_text
            if interaction
            else ""
        )

        if not output:

            raise RuntimeError(
                "Gemini returned an empty response."
            )

        print(
            "[SUCCESS] Gemini basic API is working."
        )

        print()
        print(
            "Response:"
        )

        print(
            output.strip()
        )

        results[
            "Gemini Basic API"
        ] = True

        return True

    except ModuleNotFoundError as error:

        explain_error(
            "Gemini",
            "Basic API",
            error,
        )

        print(
            "Install:"
        )

        print(
            "pip install google-genai"
        )

        return False

    except Exception as error:

        explain_error(
            "Gemini",
            "Basic API",
            error,
        )

        return False


# =========================================================
# 11. GEMINI GOOGLE SEARCH TEST
# =========================================================

def test_gemini_google_search() -> bool:

    print_header(
        "STEP 6 - GEMINI GOOGLE SEARCH TEST"
    )

    if not GEMINI_API_KEY:

        print(
            "[SKIPPED] GEMINI_API_KEY is missing."
        )

        return False

    try:

        from google import genai

        client = genai.Client(
            api_key=GEMINI_API_KEY
        )

        interaction = client.interactions.create(
            model=GEMINI_MODEL,

            input=(
                "Use Google Search to find one current "
                "software developer job opening in India. "
                "Return only the company name, job title, "
                "and direct job URL."
            ),

            tools=[
                {
                    "type": "google_search"
                }
            ],
        )

        output = (
            interaction.output_text
            if interaction
            else ""
        )

        if not output:

            raise RuntimeError(
                "Gemini Google Search returned an empty response."
            )

        print(
            "[SUCCESS] Gemini Google Search is working."
        )

        print()
        print(
            "Google Search Response:"
        )

        print(
            output.strip()
        )

        # ---------------------------------------------
        # Print citations when Gemini exposes them
        # ---------------------------------------------

        print()
        print(
            "Sources:"
        )

        source_found = False

        for step in getattr(
            interaction,
            "steps",
            [],
        ):

            if getattr(
                step,
                "type",
                None,
            ) != "model_output":

                continue

            for block in getattr(
                step,
                "content",
                [],
            ):

                annotations = getattr(
                    block,
                    "annotations",
                    None,
                )

                if not annotations:
                    continue

                for annotation in annotations:

                    title = getattr(
                        annotation,
                        "title",
                        "",
                    )

                    url = getattr(
                        annotation,
                        "url",
                        "",
                    )

                    if url:

                        source_found = True

                        print(
                            f"- {title or 'Source'}"
                        )

                        print(
                            f"  {url}"
                        )

        if not source_found:

            print(
                "- No source URL was exposed "
                "in the SDK response."
            )

        results[
            "Gemini Google Search"
        ] = True

        return True

    except ModuleNotFoundError as error:

        explain_error(
            "Gemini",
            "Google Search",
            error,
        )

        return False

    except Exception as error:

        explain_error(
            "Gemini",
            "Google Search",
            error,
        )

        return False


# =========================================================
# 12. FINAL REPORT
# =========================================================

def final_report() -> None:

    print_header(
        "FINAL RESULT"
    )

    for name, status in results.items():

        if status:

            print(
                f"[PASS] {name}"
            )

        else:

            print(
                f"[FAIL] {name}"
            )

    openai_ok = (
        results["OpenAI Basic API"]
        and results["OpenAI Web Search"]
    )

    gemini_ok = (
        results["Gemini Basic API"]
        and results["Gemini Google Search"]
    )

    print()

    print(
        "-" * 70
    )

    if openai_ok:

        print(
            "OPENAI STATUS : WORKING"
        )

    else:

        print(
            "OPENAI STATUS : NOT WORKING"
        )

    if gemini_ok:

        print(
            "GEMINI STATUS : WORKING"
        )

    else:

        print(
            "GEMINI STATUS : NOT WORKING"
        )

    print(
        "-" * 70
    )

    print()

    if openai_ok and gemini_ok:

        print(
            "FINAL: BOTH APIs AND BOTH WEB SEARCH "
            "CAPABILITIES ARE WORKING."
        )

    elif not openai_ok and not gemini_ok:

        print(
            "FINAL: BOTH APIs HAVE A PROBLEM."
        )

    elif not openai_ok:

        print(
            "FINAL: GEMINI WORKS, BUT OPENAI HAS A PROBLEM."
        )

    elif not gemini_ok:

        print(
            "FINAL: OPENAI WORKS, BUT GEMINI HAS A PROBLEM."
        )


# =========================================================
# 13. MAIN
# =========================================================

def main() -> None:

    print()
    print("=" * 70)
    print("ORBIT-JR LLM API DIAGNOSTIC TOOL")
    print("=" * 70)

    print(
        f"Project root: {PROJECT_ROOT}"
    )

    check_packages()

    config_ok = check_configuration()

    if not config_ok:

        print()

        print(
            "Fix backend/.env first."
        )

        sys.exit(1)

    # OpenAI
    openai_basic_ok = test_openai_basic()

    if openai_basic_ok:

        test_openai_web_search()

    else:

        print()
        print(
            "OpenAI web search test skipped because "
            "the basic OpenAI test failed."
        )

    # Gemini
    gemini_basic_ok = test_gemini_basic()

    if gemini_basic_ok:

        test_gemini_google_search()

    else:

        print()
        print(
            "Gemini Google Search test skipped because "
            "the basic Gemini test failed."
        )

    final_report()


if __name__ == "__main__":
    main()