# The MIT License (MIT)
#
# Copyright (c) 2011, 2013 OpenWorm.
# http://openworm.org
#
# All rights reserved. This program and the accompanying materials
# are made available under the terms of the MIT License
# which accompanies this distribution, and is available at
# http://opensource.org/licenses/MIT
#
# Contributors:
#      OpenWorm - http://openworm.org/people.html
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in all
# copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT.
# IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM,
# DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR
# OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE
# USE OR OTHER DEALINGS IN THE SOFTWARE.
from __future__ import with_statement

import math

__author__ = 'Serg Khayrulin'


class SubSection:
    def __init__(self, parent=None):
        """
        :type self: object
        """
        self.start_x = 0
        self.start_y = 0
        self.start_z = 0
        self.end_x = 0
        self.end_y = 0
        self.end_z = 0
        self.diam = 0
        self.h = 0
        self.params = {}
        self.index = -1
        self.selected = False
        self.parent = parent

    def calc_h(self):
        self.h = math.sqrt(math.pow(self.start_x - self.end_x, 2) + math.pow(self.start_y - self.end_y, 2) +
                           math.pow(self.start_z - self.end_z, 2))

    def get_param(self, p_name):
        return self.params[p_name]


class Section:
    def __init__(self, index=-1, name='', parent=None):
        self.index = index
        self.signal = -1
        self.color = 0
        self.name = name
        self.sub_sections = []
        self.selected = False
        self.parent = parent
        self.is_soma = False

    def get_mass_center(self):
        import numpy as np
        center = np.array([0.0, 0.0, 0.0])
        for sub_s in self.sub_sections:
            center[0] += (sub_s.end_x - sub_s.start_x)/2.0
            center[1] += (sub_s.end_y - sub_s.start_y)/2.0
            center[2] += (sub_s.end_z - sub_s.start_z)/2.0
        center /= float(len(self.sub_sections))
        return center

    def init_section(self, h, params):
        self.nseg = h.cas().nseg
        self.h_sec = h.cas()
        current_length = 0.0
        len_diff_section = self.h_sec.L / self.nseg
        for i in range(int(h.n3d()) - 1):
            m_s = SubSection(self)
            m_s.start_x = h.x3d(i)
            m_s.start_y = h.y3d(i)
            m_s.start_z = h.z3d(i)
            m_s.end_x = h.x3d(i + 1)
            m_s.end_y = h.y3d(i + 1)
            m_s.end_z = h.z3d(i + 1)
            m_s.diam = h.diam3d(i)
            m_s.calc_h()
            current_length += m_s.h
            x_info = int(current_length/len_diff_section)
            self.__update_data(params, m_s, float(x_info)/float(self.nseg))
            self.sub_sections.append(m_s)

    def __update_data(self, params, m_s, n=-1):
        """
        Initializing parameters what we want to get from NEURON simulation
        :param params: parameters interesting
        :param m_s: current subsection
        :param n: number of current subsection in section it defines by nseg
        """
        for p in params:
            if p in m_s.params:
                m_s.params[p][0] = self.h_sec(m_s.params[p][1])._ref_v[0]
            elif n != -1:
                m_s.params[p] = [self.h_sec(n)._ref_v[0], n]
            else:
                raise RuntimeError('Problem with initalization')
            # TODO find mode suitable way how to do it

    def update_data(self, params):
        for s_sec in self.sub_sections:
            self.__update_data(params, s_sec)

    def get_v(self):
        max_v = self.sub_sections[0].params['v'][0]
        for s_sec in self.sub_sections[1:]:
             max_v = s_sec.params['v'][0] != max_v and s_sec.params['v'][0] or max_v
        return max_v


class MyNeuron:
    def __init__(self, name='', index=0):
        self.name = name
        self.sections = {}
        self.selected = False
        self.index = index

    def init_sections(self, h, params):
        """
        Select from list of sections
        only sections for particular helper
        fill list of section ids

        :param h: hocObject
        :param params: list of parameters which we wanna track
        """
        index = 0
        for h_sec in h.allsec():
            section_name = h_sec.name()
            if section_name.startswith(self.name):
                self.sections[section_name] = Section(index, section_name, self)
                self.sections[section_name].init_section(h, params)
            index += 1

    def init_sections(self, h, params, section_list):
        """

        :param h:
        :param params:
        :param section_list: list with sections names
        :return:
        """
        if not section_list:
            print 'No sections for current neuron %s'%(self.name)
            return
        index = 0
        for h_sec in h.allsec():
            section_name = h_sec.name()
            if section_name in section_list:
                self.sections[section_name] = Section(index, section_name, self)
                self.sections[section_name].init_section(h, params)
                #if section_list.index(section_name) == 0:
                #    self.sections[section_name].is_soma = True
            index += 1
        self.__find_soma()

    def __find_soma(self):
        cur_max_sec = None
        val = 0.0
        for sec in self.sections.values():
            sorted_sub_sections_list = sorted(sec.sub_sections, key=lambda ss: ss.diam, reverse=True) #sorted by diam of subsection
            if len(sorted_sub_sections_list) != 0:
                if sorted_sub_sections_list[0].diam > val:
                    cur_max_sec = sec
                    val = sorted_sub_sections_list[0].diam
        cur_max_sec.is_soma = True

    def update_sec_data(self, params):
        """
        Update data about params for section

        :param params: list of parameters which we wanna update
        """
        for s in self.sections.values():
            s.update_data(params)

    def turn_off_selection(self):
        """
        Make selected neuron unselected
        """
        self.selected = False
        for sec in self.sections.values():
            sec.selected = False
            for sub_sec in sec.sub_sections:
                sub_sec.selected = False

    def get_selected_sub_section(self):
        """
        Get selected subsection in selected section

        :return: SubSection object
        """
        if not self.selected:
            return '', None
        sec = self.get_selected_section()
        if sec is None:
            return None
        for sub_sec in sec.sub_sections:
            if sub_sec.selected:
                return sec.name, sub_sec

    def get_selected_section(self):
        """
        Get selected subsection in selected section

        :return: SubSection object
        """
        if not self.selected:
            return None
        for name, sec in self.sections.iteritems():
            if sec.selected:
                return sec

    def get_voltage(self, section_name):
        return self.sections[section_name].get_v()