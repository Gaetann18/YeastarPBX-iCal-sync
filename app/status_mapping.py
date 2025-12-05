STATUS_MAPPING = {
    'available': {
        'label': 'Disponible',
        'color': '#28a745',  
        'bg_color': '#d4edda',
        'icon': '✓'
    },
    'lunch': {
        'label': 'En face à face pédagogique',
        'color': '#ffc107',  
        'bg_color': '#fff3cd',
        'icon': '👥'
    },
    'business_trip': {
        'label': 'Formation',
        'color': '#007bff',  
        'bg_color': '#cfe2ff',
        'icon': '📚'
    },
    'away': {
        'label': 'Absent',
        'color': '#fd7e14',  
        'bg_color': '#ffe5d0',
        'icon': '🚫'
    },
    'do_not_disturb': {
        'label': 'Ne pas déranger',
        'color': '#dc3545',  
        'bg_color': '#f8d7da',
        'icon': '🔴'
    },
    'off_work': {
        'label': 'Hors service',
        'color': '#6c757d',  
        'bg_color': '#e2e3e5',
        'icon': '⏸'
    }
}

def get_status_display(status):

    return STATUS_MAPPING.get(status, {
        'label': status,
        'color': '#6c757d',
        'bg_color': '#e2e3e5',
        'icon': '❓'
    })

def get_status_label(status):
    return get_status_display(status)['label']

def get_status_color(status):
    return get_status_display(status)['color']

def get_status_badge_html(status):
    display = get_status_display(status)
    return f'''<span class="badge" style="background-color: {display['bg_color']}; color: {display['color']}; border: 1px solid {display['color']};">
        {display['icon']} {display['label']}
    </span>'''
