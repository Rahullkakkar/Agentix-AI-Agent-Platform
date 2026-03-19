sessions = {}

def get_session(call_id):
    return sessions.get(call_id)

def create_session(call_id, runtime):
    sessions[call_id] = runtime

def delete_session(call_id):
    if call_id in sessions:
        del sessions[call_id]