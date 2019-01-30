type c:\input.txt | java -jar c:\chapas-0.742\chapas.jar -I RAW > c:\output.txt
python c:\PASdia.py c:\output.txt c:\output.tex
xelatex c:\output.tex --shell-escape
del c:\output.tex
del c:\output.aux
del c:\output.log
del c:\output.pdf
del c:\output.txt