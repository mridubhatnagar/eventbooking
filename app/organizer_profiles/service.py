from app.organizer_profiles.repository import OrganizerProfileRepository


class OrganizerProfileService:
    def __init__(self, organizer_profile_repository=None):
        self.organizer_profile_repository = (
            organizer_profile_repository or OrganizerProfileRepository()
        )

    def get_by_user_id(self, user_id):
        return self.organizer_profile_repository.get_by_user_id(user_id)

    def get_by_user_ids(self, user_ids):
        """Batch lookup — avoids one query per event when serializing a list.
        Returns {user_id: profile}."""
        profiles = self.organizer_profile_repository.list_by_user_ids(user_ids)
        return {p.user_id: p for p in profiles}

    def update_profile(self, user_id, **fields):
        profile = self.organizer_profile_repository.get_by_user_id(user_id)
        if not profile:
            raise ValueError("organizer profile not found")
        return self.organizer_profile_repository.update(profile.id, **fields)
