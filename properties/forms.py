from django import forms
from .models import Property


class PropertyForm(forms.ModelForm):

    class Meta:
        model = Property
        fields = [
            'name',
            'property_type',
            'location',
            'description',
            'monthly_rent',
        ]

        widgets = {
            'name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Enter property name'
            }),

            'property_type': forms.Select(attrs={
                'class': 'form-control'
            }),

            'location': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Enter property location'
            }),

            'description': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 4,
                'placeholder': 'Describe the property'
            }),

            'monthly_rent': forms.NumberInput(attrs={
                'class': 'form-control',
                'placeholder': 'Enter monthly rent in KES'
            }),
        }