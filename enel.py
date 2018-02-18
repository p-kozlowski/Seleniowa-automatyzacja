#!/usr/bin/python
# -*- coding: utf-8 -*-
# vim: sw=3 sts=3

import re
import sys

from selenium.common.exceptions import NoSuchElementException
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import Select

from scraper import *


class ScraperEnel(ScraperLekarzy):
    def __init__(self, parametry):
        if parametry[3]:
            self.lekarz = parametry[3]
            print 'Lekarz', self.lekarz
        else:
            self.lekarz = None

        ScraperLekarzy.__init__(self, adresStartowy="https://online.enel.pl/Account/Login",
                                naglowekWMejlu="ENEL", parametryWejsciowe=parametry[0:3])

    def _konwertujDate(self, data):
        # (TODO) enel nie pokazuje roku. to moze nie dzialac w okolicach Sylwestra
        dataTekst = '%s.%d' % (data, datetime.datetime.now().year)
        return datetime.datetime.strptime(dataTekst, "%d.%m.%Y")

    def zaloguj(self, sel):
        for i in range(3):
            sel.find_element_by_id('Login').send_keys(slownik['login'])
            sel.find_element_by_id('Password').send_keys(hasla.haslo('enel', slownik['login'], slownik.get('haslo')))
            sel.find_element_by_id('Password').send_keys(Keys.RETURN)
            time.sleep(1)
            # enel UI ma buga - czasem po kliknięciu "Zaloguj" pola formularza są czyszczone i strona nie przechodzi dalej
            try:
                sel.find_element_by_id('Login')
            except NoSuchElementException:
                return True

        print 'Logowanie nieudane. Spróbuj za chwilę'
        return False

    def odwiedzIZbierzWyniki(self, sel):
        if not self.zaloguj(sel):
            return []

        self.czekajAzSiePojawi(sel, (By.ID, "visits-slot"))

        sel.get("https://online.enel.pl/Visit/New")
        self.czekajAzSiePojawi(sel, (By.ID, 'sbtn'))
        time.sleep(2)

        Select(sel.find_element_by_id('City')).select_by_visible_text('Warszawa')
        time.sleep(2)

        print "Szukam %s" % self.specjalizacja
        spec = Select(sel.find_element_by_id('ListOfSpecialities'))
        for option in spec.options:
            if re.findall(self.specjalizacja, option.text):
                spec.select_by_value(option.get_attribute('value'))
                break

        if self.lekarz is not None:
            time.sleep(5)
            lekarze_ramka = sel.find_element_by_id('checkboxdropdownDoc')
            lekarze_ramka.click()

            # "odznacz wszystkie"
            lekarze_ramka.find_element_by_css_selector('a.select-all').click()

            lekarze = lekarze_ramka.find_elements_by_tag_name('label')
            for lekarz in lekarze:
                if re.findall(self.lekarz, lekarz.text):
                    lekarz.find_element_by_tag_name('input').click()

        data_input = sel.find_element_by_css_selector('input.form-control')
        data_input.clear()
        zakres = '%s - %s' % (datetime.datetime.now().strftime("%Y-%m-%d"), self.przed.strftime("%Y-%m-%d"))
        data_input.send_keys(zakres)
        data_input.send_keys(Keys.RETURN)

        self.czekajAzSiePojawi(sel, (By.ID, "AcptRul")).click()
        time.sleep(1)

        sel.find_element_by_id('sbtn').click()

        self.czekajAzSiePojawi(sel, (By.CSS_SELECTOR, 'div.title-badge.color2.small-padding.m-t-14'))
        time.sleep(1)

        #TODO obsluzyc paginacje

        limit = sel.find_element_by_id('limitModal')
        if limit:
            limit.find_element_by_css_selector('button.close').click()

        terminy = sel.find_elements_by_css_selector('.box-visit')
        wyniki = []

        for termin in terminy:
            data = termin.find_element_by_css_selector('div.col-md-3.col-lg-2.col-sm-6').text.strip()[0:5]
            wyniki.append([self._konwertujDate(data) ,termin.text])

        return wyniki

if __name__ == "__main__":
    ScraperEnel(sys.argv).scrapuj()
