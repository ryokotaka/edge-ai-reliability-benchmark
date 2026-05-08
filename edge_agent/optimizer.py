"""Software optimization scope for the benchmark."""


def describe_optimization_scope() -> list[str]:
    return [
        "local buffer / checkpoint recovery",
        "float-like vs quantized lightweight anomaly scoring",
        "batch SQLite writes",
        "fixed-rate vs adaptive sampling",
    ]
