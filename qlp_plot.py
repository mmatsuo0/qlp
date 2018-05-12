#!/usr/bin/env python

import argparse
import os
import pandas
import numpy
import matplotlib.pyplot
import matplotlib.dates
import datetime

fig_dir = 'fig'
table_dir = 'table'


class Pointing:
    def __init__(self, data_path):
        self.file_base, _ = os.path.splitext(os.path.basename(data_path))
        self.data_raw = pandas.read_csv(data_path)
        self.frequency = ''
        self.use_array = ''

    def read_data(self):
        data = self.data_raw.copy()
        if not data.offset.dtype == 'float64':
            data = data[data.offset != 'ERR']
            data.offset = data.offset.astype('float64')
            data.hpbw = data.hpbw.astype('float64')
        self.az = data[data.AZEL == 'AZ']
        self.el = data[data.AZEL == 'EL']
        if (len(self.az) == 0) or (len(self.el) == 0):
            print 'data are insufficient: {}'.format(self.file_base)
            quit()
        self.get_frequency(data)

    def get_frequency(self, data):
        pos1 = float(data.pos1.iloc[0])
        if 34. < pos1 < 36.:
            f = '22GHz'
        elif 19. < pos1 < 21.:
            f = '43GHz'
        elif 9. < pos1 < 11.:
            f = '86GHz'
        else:
            f = '?'

        if f != '43GHz':
            print 'skip: frequency is {}'.format(f)
            quit()

        self.frequency = f

    def add_params(self):
        self.az['daz_all'] = self.az['qlookAutoDaz'] + self.az['manualDaz']
        self.az['dd'] = self.az.daz_all - self.az.daz_all.iloc[-1]
        self.az['offset2'] = self.az.offset + self.az.dd

        self.el['del_all'] = self.el['qlookAutoDel'] + self.el['manualDel']
        self.el['dd'] = self.el.del_all - self.el.del_all.iloc[-1]
        self.el['offset2'] = self.el.offset + self.el.dd

        self.az['SN1'] = self.az.IntegINT1 / self.az.rmsIntegInt1
        self.el['SN1'] = self.el.IntegINT1 / self.el.rmsIntegInt1
        self.az['SN2'] = self.az.IntegINT2 / self.az.rmsIntegInt2
        self.el['SN2'] = self.el.IntegINT2 / self.el.rmsIntegInt2
        self.az['SN3'] = self.az.IntegINT3 / self.az.rmsIntegInt3
        self.el['SN3'] = self.el.IntegINT3 / self.el.rmsIntegInt3

    def select_array(self):
        array_list = list(self.az.ARRAY.drop_duplicates())
        sn_sum = []
        for a in array_list:
            az_t = self.az[self.az.ARRAY == a]
            el_t = self.el[self.el.ARRAY == a]
            az_t = az_t.drop_duplicates(['DATE_OBS'], keep='last')
            el_t = el_t.drop_duplicates(['DATE_OBS'], keep='last')
            sn_sum.append(az_t.SN2.sum() + el_t.SN2.sum())
        self.use_array = array_list[numpy.argmax(sn_sum)]
        self.az2 = self.az[self.az.ARRAY == self.use_array]
        self.el2 = self.el[self.el.ARRAY == self.use_array]
        self.az2 = self.az2.drop_duplicates(['DATE_OBS'], keep='last')
        self.el2 = self.el2.drop_duplicates(['DATE_OBS'], keep='last')
        if (len(self.az2) == 0) or (len(self.el2) == 0):
            print 'data are insufficient (2): {}'.format(self.file_base)
            quit()

    def calculate_offset_hpbw(self, scan):
        scan_data = eval('self.{}2'.format(scan))
        offset_mean = scan_data.offset2.mean()
        hpbw_mean = scan_data.hpbw.mean()
        if len(scan_data) == 1:
            offset_std = 0.
            hpbw_std = 0.
        else:
            offset_std = scan_data.offset2.std()
            hpbw_std = scan_data.hpbw.std()

        return offset_mean, offset_std, hpbw_mean, hpbw_std

    def output_table(self):
        pd = {}
        offset_mean_az, offset_std_az, hpbw_mean_az, hpbw_std_az = self.calculate_offset_hpbw('az')
        offset_mean_el, offset_std_el, hpbw_mean_el, hpbw_std_el = self.calculate_offset_hpbw('el')
        pd['offset_mean_az'] = offset_mean_az
        pd['offset_std_az'] = offset_std_az
        pd['hpbw_mean_az'] = hpbw_mean_az
        pd['hpbw_std_az'] = hpbw_std_az
        pd['offset_mean_el'] = offset_mean_el
        pd['offset_std_el'] = offset_std_el
        pd['hpbw_mean_el'] = hpbw_mean_el
        pd['hpbw_std_el'] = hpbw_std_el

        data = pandas.concat([self.az2, self.el2])
        pd['az'] = data.AZreal.mean()
        pd['el'] = data.ELreal.mean()
        pd['daz'] = self.az2.daz_all.iloc[-1]
        pd['del'] = self.el2.del_all.iloc[-1]
        pd['sn'] = numpy.mean([self.az2.SN2.iloc[-1], self.el2.SN2.iloc[-1]])

        pd['temp'] = data.Temp.mean()
        pd['ap'] = data.AirPress.mean()
        pd['wv'] = data.WaterVapor.mean()
        pd['ws'] = data.wind_sp.mean()
        pd['ws_std'] = data.wind_sp.std()
        pd['wd'] = data.wind_dir.mean()
        pd['wd_std'] = data.wind_dir.std()

        table_path = '{}/{}_params.txt'.format(table_dir, self.frequency)
        fmt = '{offset_mean_az},{offset_std_az},{hpbw_mean_az},{hpbw_std_az},'
        fmt += '{offset_mean_el},{offset_std_el},{hpbw_mean_el},{hpbw_std_el},'
        fmt += '{az},{el},{daz},{del},{sn},'
        fmt += '{temp},{ap},{wv},{ws},{ws_std},{wd},{wd_std}'
        header = fmt.replace('{', '').replace('}', '')
        if not os.path.exists(table_dir):
            os.mkdir(table_dir)
        if not os.path.exists(table_path):
            with open(table_path, 'w') as f:
                f.write(header + '\n')
        with open(table_path, 'a') as f:
            f.write(fmt.format(**pd) + '\n')

    def plot_data(self):
        matplotlib.rcParams['lines.linewidth'] = 1
        matplotlib.rcParams['lines.marker'] = 'o'
        matplotlib.rcParams['lines.markersize'] = 3
        matplotlib.rcParams['font.family'] = 'Times New Roman'
        matplotlib.rcParams['font.size'] = 12
        matplotlib.rcParams['axes.grid'] = True
        matplotlib.rcParams['grid.linestyle'] = ':'
        matplotlib.rcParams['mathtext.fontset'] = 'cm'

        fig = matplotlib.pyplot.figure(figsize=(10, 10))

        ax1 = fig.add_subplot(321)
        ax2 = fig.add_subplot(322)
        ax3 = fig.add_subplot(323)
        ax4 = fig.add_subplot(324)

        az_tmp = self.az2
        el_tmp = self.el2

        ax1.plot(pandas.to_datetime(az_tmp.DATE_OBS), az_tmp.offset2)
        ax1.plot(pandas.to_datetime(az_tmp.DATE_OBS), az_tmp.offset, ls='--')
        ax1.plot(pandas.to_datetime(az_tmp.DATE_OBS), az_tmp.dd)
        ax2.plot(pandas.to_datetime(el_tmp.DATE_OBS), el_tmp.offset2)
        ax2.plot(pandas.to_datetime(el_tmp.DATE_OBS), el_tmp.offset, ls='--')
        ax2.plot(pandas.to_datetime(el_tmp.DATE_OBS), el_tmp.dd)
        ax3.plot(pandas.to_datetime(az_tmp.DATE_OBS), az_tmp.hpbw)
        ax4.plot(pandas.to_datetime(el_tmp.DATE_OBS), el_tmp.hpbw)

        ax5 = fig.add_subplot(6, 2, 9)
        ax6 = fig.add_subplot(6, 2, 10)
        ax5.plot(pandas.to_datetime(az_tmp.DATE_OBS), az_tmp.SN2)
        ax5.plot(pandas.to_datetime(az_tmp.DATE_OBS), az_tmp.SN1)
        ax5.plot(pandas.to_datetime(az_tmp.DATE_OBS), az_tmp.SN3)
        ax6.plot(pandas.to_datetime(el_tmp.DATE_OBS), el_tmp.SN2, label='center')
        ax6.plot(pandas.to_datetime(el_tmp.DATE_OBS), el_tmp.SN1, label='pos1')
        ax6.plot(pandas.to_datetime(el_tmp.DATE_OBS), el_tmp.SN3, label='pos3')
        ax6.legend(loc='lower right', ncol=3, fontsize=8)

        if self.frequency == '22GHz':
            min_hpbw = 50
            max_hpbw = 100
        elif self.frequency == '43GHz':
            min_hpbw = 20
            max_hpbw = 60
        elif self.frequency == '86GHz':
            min_hpbw = 10
            max_hpbw = 30
        else:
            min_hpbw = 10
            max_hpbw = 100

        ax1.set_title('Azimuth scan', y=1.35)
        ax1.set_ylabel("offset ($''$)")
        ax1.set_ylim(-15, 15)
        ax2.set_title('Elevation scan', y=1.35)
        ax2.set_ylim(-15, 15)
        ax3.set_ylabel("HPBW ($''$)")
        ax3.set_ylim(min_hpbw, max_hpbw)
        ax4.set_ylim(min_hpbw, max_hpbw)
        ax5.set_ylabel('S/N')
        object_name = az_tmp.OBJECT.iloc[0]
        ax5.text(0, 0.8, object_name, transform=ax5.transAxes)
        peak_az_id = az_tmp['peakTa*2'].idxmax()
        peak_el_id = el_tmp['peakTa*2'].idxmax()
        peak_az = az_tmp['peakTa*2'].loc[peak_az_id]
        peak_el = el_tmp['peakTa*2'].loc[peak_el_id]
        peak = max([peak_az, peak_el])
        ax5.text(0, 0.65, 'max $T_\mathrm{A}^*$:' + '{:.1f} K'.format(peak), transform=ax5.transAxes)
        if numpy.argmax([peak_az, peak_el]) == 0:
            ax5.plot(pandas.to_datetime(az_tmp.DATE_OBS.loc[peak_az_id]), az_tmp.SN2.loc[peak_az_id], c='r')
        elif numpy.argmax([peak_az, peak_el]) == 1:
            ax6.plot(pandas.to_datetime(el_tmp.DATE_OBS.loc[peak_el_id]), el_tmp.SN2.loc[peak_el_id], c='r')

        ax7 = fig.add_subplot(6, 2, 11)
        ax7.plot(pandas.to_datetime(az_tmp.DATE_OBS), az_tmp.wind_sp)
        ax7.set_ylabel('wind speed (km s$^{-1}$)')
        ax7.set_ylim(0, 10)
        ax8 = fig.add_subplot(6, 2, 12)
        ax8.plot(pandas.to_datetime(el_tmp.DATE_OBS), el_tmp.wind_sp)
        ax8.set_ylim(0, 10)

        day = self.az.DATE_OBS.iloc[0].split()[0]
        fig.suptitle(day)

        dt_az = (pandas.to_datetime(az_tmp.DATE_OBS.iloc[-1]) - pandas.to_datetime(az_tmp.DATE_OBS.iloc[0])).seconds
        dt_el = (pandas.to_datetime(el_tmp.DATE_OBS.iloc[-1]) - pandas.to_datetime(el_tmp.DATE_OBS.iloc[0])).seconds

        if (dt_az == 0) or (dt_el == 0):
            xlocater = matplotlib.dates.MinuteLocator(interval=1)
            date_fmt = '%H:%M:%S'
            xlim1_az = pandas.to_datetime(az_tmp.DATE_OBS.iloc[0]) - datetime.timedelta(minutes=1)
            xlim2_az = pandas.to_datetime(az_tmp.DATE_OBS.iloc[-1]) + datetime.timedelta(minutes=1)
            xlim1_el = pandas.to_datetime(el_tmp.DATE_OBS.iloc[0]) - datetime.timedelta(minutes=1)
            xlim2_el = pandas.to_datetime(el_tmp.DATE_OBS.iloc[-1]) + datetime.timedelta(minutes=1)
            for i in [1, 3, 5, 7]:
                eval('ax{}.set_xlim(xlim1_az, xlim2_az)'.format(i))
                eval('ax{}.set_xlim(xlim1_el, xlim2_el)'.format(i+1))
        elif dt_az > 1800:
            xlocater = matplotlib.dates.MinuteLocator(interval=10)
            date_fmt = '%H:%M'
        elif dt_az > 900:
            xlocater = matplotlib.dates.MinuteLocator(interval=5)
            date_fmt = '%H:%M'
        elif dt_az > 120:
            xlocater = matplotlib.dates.MinuteLocator(interval=2)
            date_fmt = '%H:%M'
        else:
            xlocater = matplotlib.dates.MinuteLocator(interval=2)
            date_fmt = '%H:%M:%S'

        for i in range(1, 9):
            eval('ax{}.xaxis.set_major_locator(xlocater)'.format(i))
            eval('ax{}.xaxis.set_major_formatter(matplotlib.dates.DateFormatter(date_fmt))'.format(i))

        fig.text(0.05, 0.98, 'Frequency: {}'.format(self.frequency))
        fig.text(0.05, 0.96, 'Array: {}'.format(self.use_array))
        fig.text(0.8, 0.98, '(dAZ, dEL) = ({:+.2f}, {:+.2f})'.format(self.az2.daz_all.iloc[-1], self.el2.del_all.iloc[-1]))

        ddaz2, time_ddaz2 = self.get_dd('az')
        ddel2, time_ddel2 = self.get_dd('el')
        text_yoffset_az = ax1.get_ylim()[1]
        for t in range(len(ddaz2)):
            ax1.text(pandas.Timestamp(time_ddaz2.iloc[t]), text_yoffset_az, '{:+.1f}'.format(ddaz2[t]), horizontalalignment='center', fontsize=9)
            ax1.axvline(pandas.Timestamp(time_ddaz2.iloc[t]), c='k', marker='')
        text_yoffset_el = ax2.get_ylim()[1]
        for t in range(len(ddel2)):
            ax2.text(pandas.Timestamp(time_ddel2.iloc[t]), text_yoffset_el, '{:+.1f}'.format(ddel2[t]), horizontalalignment='center', fontsize=9)
            ax2.axvline(pandas.Timestamp(time_ddel2.iloc[t]), c='k', marker='')

        ax9 = fig.add_axes([0.12, 0.89, 0.35, 0.07])
        ax10 = fig.add_axes([0.54, 0.89, 0.35, 0.07])
        self.plot_table('az', ax9)
        self.plot_table('el', ax10)

        self.fig = fig

    def save_figure(self):
        if not os.path.exists(fig_dir):
            os.mkdir(fig_dir)
        if not os.path.exists(os.path.join(fig_dir, self.frequency)):
            os.mkdir(os.path.join(fig_dir, self.frequency))

        print 'saved: {}'.format(self.file_base)
        save_file = '{}/{}/{}.png'.format(fig_dir, self.frequency, self.file_base)
        self.fig.savefig(save_file)
        self.fig.clf()

    @staticmethod
    def show_figure():
        matplotlib.pyplot.show()

    def show_figure_gui(self):
        self.fig.show()

    def get_dd(self, scan):
        scan_data = eval('self.{}2'.format(scan))
        dd = numpy.array(scan_data['d{}_all'.format(scan)])[1:] \
            - numpy.array(scan_data['d{}_all'.format(scan)])[:-1]
        dd = numpy.insert(dd, 0, 0.)
        dd2 = dd[numpy.where(dd != 0.)[0]]
        time_dd2 = scan_data['DATE_OBS'].iloc[numpy.where(dd != 0.)[0]]
        return dd2, time_dd2

    def plot_table(self, scan, ax):
        offset_mean, offset_std, hpbw_mean, hpbw_std = self.calculate_offset_hpbw(scan)

        ax.patch.set_alpha(0)
        ax.axis('off')
        ax.axhline(0.1, c='k', marker='', linewidth=0.4)
        ax.axhline(0.4, c='k', marker='', linewidth=0.4)
        ax.axhline(0.7, c='k', marker='', linewidth=0.4)
        ax.axvline(0.2, ymin=0.1, c='k', marker='', linewidth=0.4)
        ax.axvline(0.5, ymin=0.1, c='k', marker='', linewidth=0.4)
        ax.text(0.05, 0.45, 'offset')
        ax.text(0.05, 0.15, 'HPBW')
        ax.text(0.28, 0.75, 'Average')
        ax.text(0.55, 0.75, 'Standard Deviation')

        ax.text(0.3, 0.45, "{:+.1f}$''$".format(offset_mean))
        ax.text(0.7, 0.45, "{:.1f}$''$".format(offset_std))
        ax.text(0.3, 0.15, "{:+.1f}$''$".format(hpbw_mean))
        ax.text(0.7, 0.15, "{:.1f}$''$".format(hpbw_std))


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('file_path')
    args = parser.parse_args()

    qlp = Pointing(args.file_path)
    qlp.read_data()
    qlp.add_params()
    qlp.select_array()
    # qlp.output_table()
    qlp.plot_data()
    # qlp.save_figure()
    qlp.show_figure()
