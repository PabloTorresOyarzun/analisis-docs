# AWS Read

## Tabla de Contenido

- [Acerca de](#about)
- [Primeros pasos ](#getting_started)
- [Uso](#usage)

## Acerca de <a name = "about"></a>

AWS Read es una aplicación Flask que extrae texto e informacion importante de archivos que incluyan texto. Con la finalidad de categorizar y rescatar los datos importantes y mejorar la legibilidad

## Primeros pasos <a name = "getting_started"></a>

Estas instrucciones te permitirán obtener una copia del proyecto y ejecutarlo en tu máquina local para fines de desarrollo y pruebas

### Prerrequisitos

Qué necesitas para instalar la APP

```
Python 1.10.2
Docker
git
```

### Instalación

Para instalar y levantar la aplicación esn necesario seguir los siguientes pasos.

#### 1- **Clonar repositorio**: en CMD corre el siguiente comando.

```cmd
git clone https://github.com/PabloTorresOyarzun/analisis-docs.git
```

#### 2- **Levantar App con Docker**: en CMD corre el siguiente comando.
> [!WARNING]  
> Debe estar docker corriendo de fondo, de lo contrario no se levantara.
```
docker-compose up
```

#### 3- **Ingresar a la App**:
En consola aparecera la URL con el puerto en donde se encuentra la app, por lo general es: [127.0.0.1:5000](http://127.0.0.1:5000)

#### 4- **Apagar App con Docker**: en CMD corre el siguiente comando.

```
docker-compose down
```

## Uso <a name = "usage"></a>

> [!NOTE]  
> Cuando se realicen cambios en el codigo, se debe correr `docker-compose up --build` en consola para actualizar el contenedor.
"# aws-textract" 
