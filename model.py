"""Intent-model loading with a clear error instead of an import-time crash.

The saved files are read lazily on first use, not at ``import`` time, so
``import model`` never performs disk I/O. Callers get ``ModelLoadError``
with a retrain hint when the files are missing, corrupt, or built with an
incompatible scikit-learn.
"""
import pickle
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent

MIN_CONFIDENCE = 0.12


class ModelLoadError(RuntimeError):
    """Raised when the saved intent model cannot be loaded or used."""


_model_cache = {}


def _load_pair():
    """Load and cache (vectorizer, model), raising ModelLoadError on failure."""
    if "vectorizer" in _model_cache:
        return _model_cache["vectorizer"], _model_cache["model"]
    try:
        with open(BASE_DIR / "vectorizer.pkl", "rb") as f:
            vectorizer = pickle.load(f)
        with open(BASE_DIR / "intent_model.pkl", "rb") as f:
            model = pickle.load(f)
    except (OSError, EOFError, pickle.PickleError, ValueError, AttributeError, ImportError) as error:
        raise ModelLoadError(
            f"Cannot load intent model files from {BASE_DIR}. "
            "Run training first: venv/bin/python train.py "
            f"({error.__class__.__name__}: {error})"
        ) from error

    if not hasattr(vectorizer, "transform") or not hasattr(model, "predict_proba"):
        raise ModelLoadError(
            f"Intent model files in {BASE_DIR} are corrupt "
            "(missing transform/predict_proba). "
            "Re-run: venv/bin/python train.py"
        )

    _model_cache["vectorizer"] = vectorizer
    _model_cache["model"] = model
    return vectorizer, model


def __getattr__(name):
    # PEP 562: keep `model.model` / `model.vectorizer` working without
    # reading files at import time.
    if name in ("model", "vectorizer"):
        vectorizer, model = _load_pair()
        return model if name == "model" else vectorizer
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


def predict_intent(text):
    vectorizer, model = _load_pair()
    vec = vectorizer.transform([text])
    probabilities = model.predict_proba(vec)[0]
    best_index = probabilities.argmax()

    if probabilities[best_index] < MIN_CONFIDENCE:
        return "unknown"

    return model.classes_[best_index]
