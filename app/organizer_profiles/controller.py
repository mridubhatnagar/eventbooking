from flask import Blueprint, request
from flask_jwt_extended import get_jwt_identity

from app.decorators import role_required
from app.organizer_profiles.service import OrganizerProfileService
from app.organizer_profiles.schemas import UpdateOrganizerProfileRequest
from app.enums import Role
from app.docs import api, JWT_SECURITY
from app.responses import success, error

bp = Blueprint("organizer_profiles", __name__, url_prefix="/organizers")
organizer_profile_service = OrganizerProfileService()


def _serialize(profile):
    return {
        "id": profile.id,
        "user_id": profile.user_id,
        "company_name": profile.company_name,
        "city": profile.city,
        "address": profile.address,
        "industry": profile.industry,
        "gst_number": profile.gst_number,
        "pan_number": profile.pan_number,
        "bank_account_holder_name": profile.bank_account_holder_name,
        "bank_account_number": profile.bank_account_number,
        "bank_ifsc_code": profile.bank_ifsc_code,
        "bank_name": profile.bank_name,
        "created_at": profile.created_at.isoformat(),
    }


@bp.patch("/me")
@role_required(Role.ORGANIZER)
@api.validate(
    json=UpdateOrganizerProfileRequest,
    tags=["organizer-profiles"],
    security=JWT_SECURITY,
)
def update_my_profile():
    data = request.context.json
    fields = data.model_dump(exclude_none=True)
    user_id = int(get_jwt_identity())

    try:
        profile = organizer_profile_service.update_profile(user_id, **fields)
    except ValueError as e:
        return error(str(e), 404)

    return success(_serialize(profile), 200)
