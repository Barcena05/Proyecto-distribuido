import requests

requests.get('http://127.0.0.1:5000/preprocess')

print("Bienvenido al buscador\n")

while True:
    print("Desea descargar archivos(0) o subir archivos(1)?")
    entry = int(input())

    if entry == 0:
        query = input('Por favor introduzca la consulta:\n')
        format_entry_bool = input('Desea filtrar por formatos? (S/N)\n').lower()
        format_entry_bool = True if format_entry_bool == 's' else False
        file_format = 'Any'
        if format_entry_bool:
            file_format = input('Introduzca el formato (ej: txt, mp3, etc)\n').lower()
        
        response = requests.get(f'http://localhost:5000/query/{query}/{file_format}')   
        if response.status_code == 200:
            body = response.json()
            for item in body:
                print(item)
            
            quantity = int(input('Cuantos archivos desea recuperar?\n'))
            if not type(quantity) is int or quantity<0:
                quantity = 1
                
            for item in body:
                if quantity == 0:
                    break
                download_response = requests.get(f'http://localhost:5000/download/{item[0]}/{item[1]}')
                if download_response.status_code == 200:
                    download_name = download_response.headers.get('Content-Disposition').split('filename=')[-1]
                    with open(f'data/{download_name}', 'wb') as file:
                        file.write(download_response.content)
                    print('Archivo descargado correctamente')
                    quantity -= 1
                else:
                    print("Error al descargar el archivo")
        else:   
            print('No se encontró el archivo') 
    elif entry == 1:
        file_name = input('Por favor introduzca el archivo:\n')
        with open(f'data/{file_name}', 'rb') as file:
            file_content = file.read()
            requests.post(f'http://localhost:5000/upload/{file_name}', files={f'{file_name}': file_content})
        
    if input("Presione q para salir o cualquier otra tecla para volver a buscar\n").lower() == 'q':
        break