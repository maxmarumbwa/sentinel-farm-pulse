from django.shortcuts import render
from django.shortcuts import render

def analytics(request):
    # Placeholder function
    data = {
        "ndvi": 0.75,
        "evi": 0.65,
        "savi": 0.70,
    }
    return render(request, "vegetation_data.html", data)
