#### HELPER FUNCTIONS
def get_user_id(phone_number: str) -> int:
    """
    This function will only be called after it is verified that is_guest
    :param phone_number: A guest's phone number in str format
    :return: The first guest_id from the db with the passed in phone number
    """
    return Guest.query.filter_by(phone_number=phone_number).first()


def is_guest(phone_number: str) -> bool:
    """
    TODO we should normalize phone numbers before adding to db and before querying db
    Checks if phone number belongs to a guest entry on db
    :param phone_number: A phone number in str format
    :return: True if entry is found, False otherwise
    """

    return db.session.query(exists().where(Guest.phone_number == phone_number))


def is_user_checked_in(guest_id: int) -> bool:
    """
    function only called after it is verified that user exists
    :param guest_id: an unique id from Guest db
    :return: True if guest is checked in, False otherwise
    """
    guest = Guest.query.get(guest_id)
    return guest.is_checked_in

