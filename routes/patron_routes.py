"""
Patron Routes - Patron status report
"""

from flask import Blueprint, render_template, request
from services.library_service import get_patron_status_report

patron_bp = Blueprint('patron', __name__)

@patron_bp.route('/patron_status', methods=["GET"])
def patron_status():
    """
    Display patron status for a particular patron.
    Web interface for R7: Patron Status Report
    """
    patron_id = request.args.get("patron_id")
    
    if not patron_id:
        return render_template('patron_status.html', error="Must enter a patron id.")
    
    # Use business logic function
    patron_info = get_patron_status_report(patron_id)
    
    if not patron_info:
        return render_template('patron_status.html', error="Patron not found.")
    
    return render_template('patron_status.html', patron_id=patron_id, patron_info=patron_info)