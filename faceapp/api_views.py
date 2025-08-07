# faceapp/api_views.py
from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework import status
from .models import KnownPerson, Attendance
from django.utils import timezone

@api_view(['POST'])
def mark_attendance(request):
    email = request.data.get("email")
    shivir = request.data.get("shivir")

    if not email or not shivir:
        return Response({"error": "Email and shivir are required."}, status=status.HTTP_400_BAD_REQUEST)

    try:
        person = KnownPerson.objects.get(email=email)
    except KnownPerson.DoesNotExist:
        return Response({"error": "Person not found."}, status=status.HTTP_404_NOT_FOUND)

    # ✅ NEW: Check if person is active
    if not person.is_active:
        return Response({
            "error": "Attendance cannot be marked for inactive person.",
            "reason": person.deactivated_reason or "Person is deactivated",
            "deactivated_since": person.deactivated_date
        }, status=status.HTTP_403_FORBIDDEN)

    # Check if person is blacklisted
    if person.is_blacklisted:
        return Response({
            "error": "Attendance cannot be marked for blacklisted person.",
            "reason": person.blacklisted_reason or "Person is blacklisted",
            "blacklisted_since": person.blacklisted_date
        }, status=status.HTTP_403_FORBIDDEN)

    today = timezone.now().date()
    already_marked = Attendance.objects.filter(person=person, timestamp__date=today, session=shivir).exists()

    if not already_marked:
        Attendance.objects.create(person=person, session=shivir)
        return Response({"success": f"Attendance marked successfully for {shivir}!"})
    else:
        return Response({"info": f"Attendance already marked for {shivir}."})

# ✅ NEW: User activation/deactivation API endpoints
@api_view(['POST'])
def activate_person(request):
    email = request.data.get("email")
    
    if not email:
        return Response({"error": "Email is required."}, status=status.HTTP_400_BAD_REQUEST)
    
    try:
        person = KnownPerson.objects.get(email=email)
        person.is_active = True
        person.deactivated_reason = ""
        person.deactivated_date = None
        person.save()
        
        return Response({
            "success": f"{person.name} has been activated.",
            "activated_date": timezone.now()
        })
    except KnownPerson.DoesNotExist:
        return Response({"error": "Person not found."}, status=status.HTTP_404_NOT_FOUND)

@api_view(['POST'])
def deactivate_person(request):
    email = request.data.get("email")
    reason = request.data.get("reason", "Deactivated via API")
    
    if not email:
        return Response({"error": "Email is required."}, status=status.HTTP_400_BAD_REQUEST)
    
    try:
        person = KnownPerson.objects.get(email=email)
        person.is_active = False
        person.deactivated_reason = reason
        person.deactivated_date = timezone.now()
        person.save()
        
        return Response({
            "success": f"{person.name} has been deactivated.",
            "reason": reason,
            "deactivated_date": person.deactivated_date
        })
    except KnownPerson.DoesNotExist:
        return Response({"error": "Person not found."}, status=status.HTTP_404_NOT_FOUND)

@api_view(['GET'])
def activation_status(request, email):
    try:
        person = KnownPerson.objects.get(email=email)
        return Response({
            "name": person.name,
            "email": person.email,
            "is_active": person.is_active,
            "deactivated_reason": person.deactivated_reason,
            "deactivated_date": person.deactivated_date,
            "is_blacklisted": person.is_blacklisted,
            "blacklisted_reason": person.blacklisted_reason,
            "blacklisted_date": person.blacklisted_date
        })
    except KnownPerson.DoesNotExist:
        return Response({"error": "Person not found."}, status=status.HTTP_404_NOT_FOUND)

# Existing blacklist endpoints...
@api_view(['POST'])
def blacklist_person(request):
    email = request.data.get("email")
    reason = request.data.get("reason", "Blacklisted via API")
    
    if not email:
        return Response({"error": "Email is required."}, status=status.HTTP_400_BAD_REQUEST)
    
    try:
        person = KnownPerson.objects.get(email=email)
        person.is_blacklisted = True
        person.blacklisted_reason = reason
        person.blacklisted_date = timezone.now()
        person.save()
        
        return Response({
            "success": f"{person.name} has been blacklisted.",
            "reason": reason,
            "blacklisted_date": person.blacklisted_date
        })
    except KnownPerson.DoesNotExist:
        return Response({"error": "Person not found."}, status=status.HTTP_404_NOT_FOUND)

@api_view(['POST'])
def unblacklist_person(request):
    email = request.data.get("email")
    
    if not email:
        return Response({"error": "Email is required."}, status=status.HTTP_400_BAD_REQUEST)
    
    try:
        person = KnownPerson.objects.get(email=email)
        person.is_blacklisted = False
        person.blacklisted_reason = ""
        person.blacklisted_date = None
        person.save()
        
        return Response({"success": f"{person.name} has been removed from blacklist."})
    except KnownPerson.DoesNotExist:
        return Response({"error": "Person not found."}, status=status.HTTP_404_NOT_FOUND)

@api_view(['GET'])
def blacklist_status(request, email):
    try:
        person = KnownPerson.objects.get(email=email)
        return Response({
            "name": person.name,
            "email": person.email,
            "is_blacklisted": person.is_blacklisted,
            "blacklisted_reason": person.blacklisted_reason,
            "blacklisted_date": person.blacklisted_date
        })
    except KnownPerson.DoesNotExist:
        return Response({"error": "Person not found."}, status=status.HTTP_404_NOT_FOUND)
