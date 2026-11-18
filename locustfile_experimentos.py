# ENCABEZADO
'''
Titulo: Tiendita (archivo locustfile.py)
Autor: Esther Bautista
Fecha de creación: 28 de octubre de 2026
Descripción: Archivo de configuración para Locust en el proyecto Tiendita. 

EJECUTAR CON: "locust -f locustfile_experimentos.py"

'''


from locust import HttpUser, task, between

class ClienteTienditaAsincrona(HttpUser):
    # Un tiempo de espera extremadamente bajo para que los 100 usuarios
    # ataquen la API prácticamente en el mismo milisegundo (Concurrencia pura)
    wait_time = between(0.001, 0.01)

    @task
    def comprar_cafe(self):
        """
        Envía peticiones PUT masivas para comprar el Café (ID 3).
        Diseñado para estresar el stock de 15 unidades simultáneamente.
        """
        # Pasamos la cantidad por query params tal como lo definiste en tu FastAPI
        url = "/productos/3/comprar?cantidad_comprada=1"
        
        # catch_response=True es obligatorio para el Experimento B
        with self.client.put(url, catch_response=True) as response:
            # En el Experimento A y al inicio del B, las peticiones exitosas devuelven 200 OK
            if response.status_code == 200:
                response.success()
            
            # En el Experimento B, cuando el stock llega a 0, las +99 peticiones restantes 
            # deben ser rechazadas ordenadamente con un 400 Bad Request. 
            # Le indicamos a Locust que esto es un éxito esperado de la prueba, no una falla del servidor.
            elif response.status_code == 400:
                response.success()
            
            # Si da cualquier otro error (500, 404, etc.), sí lo reportamos como falla real
            else:
                response.failure(f"Error inesperado: {response.status_code} - {response.text}")
