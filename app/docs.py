from spectree import SpecTree

api = SpecTree(
    "flask",
    title="Event Booking System API",
    version="1.0.0",
    validation_error_status=400,
    mode="strict",
)
