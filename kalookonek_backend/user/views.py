from django.shortcuts import render
from django.http import HttpResponse 

# Create your views here.

def dashboard(request):
    if request.method == 'GET':
        pass

def user(request):
    if request.method == 'GET':
        pass
        
    elif request.method == 'UPDATE':
        pass

def health_record(request):
    if request.method == 'GET':
        pass

def qr_code(request):
    if request.method == 'GET':
        pass

def emergency_contacts(request):
    if request.method == 'GET':
        pass

def medicine(request):
    if request.method == 'GET':
        pass
    elif request.method == 'POST':
        pass

def appointments(request):
    if request.method == 'GET': # when user views their appointments
        pass
    elif request.method == 'POST': # when user requests for an appointment
        pass