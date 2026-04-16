from django.shortcuts import render
from django.http import HttpResponse, JsonResponse

def dashboard(request):
    if request.method == 'GET':
        #pass
         return HttpResponse("mp dashboard ok")

def mp(request):
    if request.method == 'GET':
        pass
        #return HttpResponse("mp profile ok")
    elif request.method == 'PUT':
        pass
        #return HttpResponse("mp profile updated")

def patient_directory(request): 
    if request.method == 'GET':
        pass
        #return HttpResponse("mp patient directory ok")

def search_patient_by_name(request):
    if request.method == 'GET':
        pass
        #return HttpResponse("mp search patient by name ok")

def search_filter_barangay(request):
    if request.method == 'GET':
        pass
        #return HttpResponse("mp search filter barangay ok")

def patient_record(request, patient_id):
    if request.method == 'GET':
        pass
        #return HttpResponse("mp patient record ok")
    elif request.method == 'PUT':
        pass
        #return HttpResponse("mp patient record updated")

def schedule(request):
    if request.method == 'GET':
        pass
        #return HttpResponse("mp schedule ok")

def schedule_history(request):
    if request.method == 'GET':
        pass
        #return HttpResponse("mp schedule history ok")