# Règles CSS

## Pour ajouter des propriétés css

1. Utiliser en premier lieu des classes du DSFR, détaillées ici : https://www.systeme-de-design.gouv.fr/
2. Si aucun élément du dsfr ne permet de répondre au besoin, alors créer une classe de la forme suivante :

'balise-specific-cssAttribute-value'

Par exemple, pour ajouter une hauteur de 85 pixel à une div, la classe sera :

'div-specific-height-85px'

La balise est optionnelle, la classe pourrait être :

'specific-height-85px'

3. Ajouter les attributs et valeurs de cette classe dans un fichier du même nom que le fichier html dans lequel la classe est appelée. Reprendre la même architecture de dossier que le fichier html en question pour le fichier css dans le dossier static associé.

Par exemple, le fichier home.html se trouve dans :

- recoco/apps/home/templates/home/home.html

Alors le fichier home.css devra se trouver dans :

- recoco/apps/home/static/css/home/home.css
