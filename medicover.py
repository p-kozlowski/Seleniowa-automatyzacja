#!/usr/bin/python
# -*- coding: utf-8 -*-
# vim: sw=3 sts=3

from selenium import selenium
import sys, time, os, datetime, hashlib
import socket
import smtplib
import pprint
import datetime
import traceback
from email.MIMEText import MIMEText
from email.Charset import Charset

from ustawienia import slownik
try:
   from ustawienia import konta
except ImportError:
   konta = {}


parametry = sys.argv[1:4]
dopisaneRegExp = [{True: "", False: "regexp:"+i}[i==""] for i in parametry]
specjalizacja, doktor, centrum = tuple([dopisaneRegExp[i] for i in [0,1,2]])

przed = datetime.datetime.strptime(sys.argv[4], "%Y-%m-%d")

if len(sys.argv) > 5:
   login = sys.argv[5]
   slownik_konta = konta.get(login, {})
   slownik_konta.setdefault('login', login)
   slownik.update(slownik_konta)

print "Szukamy dla loginu %s:" % (slownik['login'],)
print "- specjalizacji "+specjalizacja
print "- doktora       "+doktor
print "- centrum       "+centrum
print "Wizyta przed "+str(przed)

def pozbadzSiePolskichLiter(text):
   dic = {u'ą':'a', u'ć':'c', u'ę':'e', u'ł':'l', u'ń':'n', u'ó':'o', u'ś':'s', u'ź':'z', u'ż':'z', 
          u'Ą':'A', u'Ć':'C', u'Ę':'E', u'Ł':'L', u'Ń':'N', u'Ó':'O', u'Ś':'S', u'Ź':'Z', u'Ż':'Z', 
	 } 
   for org, nowa in dic.iteritems():
       text = text.replace(org, nowa)
   return text


def mejl(tabelka, ustawieniaMejla):
   od, do, smtp = tuple([ustawieniaMejla[x] for x in ["od", "do", "smtp"]])
   tekst = "<h2>Wyniki</h2>" +"<ul>"
   
   for dzien in tabelka.keys():
      tekst=tekst + "<li>"+dzien + "<ol>"
      for wynikDnia in tabelka[dzien]:
         tekst=tekst + "<li>"+wynikDnia+"</li>"
      tekst=tekst+"</ol></li>"   
   
   tekst = tekst + ("</ul>" +"<br/>\r-- " +"<br/>\r %s") \
     % datetime.datetime.now().__str__()
   
   
   temat="[MEDICOVER] %s" % (datetime.datetime.now())

   charset=Charset('utf-8')
   tresc=MIMEText(tekst.encode('utf-8'), 'html')
   tresc.set_charset(charset)
   tresc['From'] = od
   tresc['To'] = ", ".join(do)
   tresc['Subject'] = temat

   serwer=smtplib.SMTP(smtp)
   serwer.sendmail(od,do,tresc.as_string())
   serwer.quit()    

def wybierz(selenium, id, wartosc):
   selenium.select(id, wartosc)
   selenium.fire_event(id, 'change')
   time.sleep(2)
   

dzien = 864000000000

adres="https://online.medicover.pl/WAB3/"

sel = selenium(slownik["selenium"]["host"], slownik["selenium"]["port"], '*firefox /usr/bin/firefox', adres)
try:
  sel.start()
  sel.open(adres)

  sel.wait_for_page_to_load(10000)  

  sel.type('id=txUserName', slownik["login"])
  sel.type('id=txPassword', slownik["haslo"])
  sel.click('id=btnLogin')
  sel.wait_for_page_to_load(20000)

  sel.click('id=btnNext')
  sel.wait_for_page_to_load(10000)

  sel.click('id=btnBookAppointment')
  sel.wait_for_page_to_load(10000)

  sel.select('id=cboRegion', 'Warszawa')
  time.sleep(2)
  
  if specjalizacja:
   wybierz(sel, 'id=cboSpecialty', specjalizacja) 
  if sel.is_element_present('id=chkFollowUpVisit'):	# pojawia się po wyborze "Pediatra"
   sel.click('id=chkFollowUpVisit')
   time.sleep(2)
  if doktor:
   wybierz(sel, 'id=cboDoctor', doktor) 
  if centrum:
   wybierz(sel, 'id=cboClinic', centrum)

  wynik={}

  for i in range(3): 
   sel.click('id=btnSearch')
   sel.wait_for_page_to_load(10000)
   time.sleep(3)
   if sel.is_element_present('id=dgGrid'):
     break
   else:
     if not sel.is_element_present('btnOK'):
        print "Przerywamy iteracje po %d" % (i)
        break
     sel.click('btnOK')
     sel.wait_for_page_to_load(10000)
     time.sleep(3)
     komponentZData = "//input[@name='dtpStartDateTicks']"
     
     biezacaWartoscPoczatku = int(sel.get_value(komponentZData))
     sel.type(komponentZData, str(biezacaWartoscPoczatku + 7 * dzien)) 
  
  dzis = datetime.datetime.now()
  
  while sel.is_element_present('id=dgGrid'):  
     dataNapis = sel.get_table('dgGrid.0.0').strip().split(" ")[1].__str__()
     data = datetime.datetime.strptime(dataNapis, "%d/%m/%Y")
     
     zaIleDni = (data-dzis).days
     if data > przed:
       print "Wybieglismy juz %d dni w przyszlosc, konczymy" % zaIleDni
       break
       
     wynikiTegoDnia=[]  
     wynik[data.strftime("%d-%m-%Y (%A)")] = wynikiTegoDnia  

     ileWierszy = int(sel.get_xpath_count("//*[@id='dgGrid']/*/*"))
     for wiersz in range(ileWierszy):
        komorki = [pozbadzSiePolskichLiter(sel.get_table('dgGrid.%d.%d' % (wiersz,kolumna))) for kolumna in [1,2,3]]
        print data, komorki
        wynikiTegoDnia.append(" ".join(komorki))
        
     nextDay="xpath=//input[@id='btnNextDay'][not(@disabled)]" 
     if sel.is_element_present(nextDay):
         sel.click(nextDay)
         sel.wait_for_page_to_load(10000)
         time.sleep(1)
     else:
         break          

  wynikSformatowany=pprint.pformat(wynik)

  md5 = hashlib.md5()
  md5.update(wynikSformatowany)
  skrot = 'pamiec/%s' % (md5.hexdigest())
  if os.path.exists(skrot):
    print "NIC NOWEGO"
  else:
    print "Cos nowego: ", wynik
    plik = open(skrot, 'w')
    plik.write(wynikSformatowany)
    plik.close()
    mejl(wynik, slownik["email"])

finally:
   try:
      sel.close()
      time.sleep(2)
      sel.stop()
      time.sleep(2)
   except:
      traceback.print_exc()
