# MicroPython SSD1306 OLED driver, I2C and SPI interfaces
from micropython import const
from machine import SoftI2C,Pin         #从machine模块导入I2C、Pin子模块
import framebuf

class SSD1306(framebuf.FrameBuffer):
    def __init__(self, width, height, external_vcc):
        self.width = width
        self.height = height
        self.x_offset = 0
        self.external_vcc = external_vcc
        self.pages = self.height // 8
        self.buffer = bytearray(self.pages * self.width)
        super().__init__(self.buffer, self.width, self.height, framebuf.MONO_VLSB)
        self.init_display()
    def init_display(self):
        hex_values = [
            0xAE,  # display off
            0xD5,  # set osc division
            0xF0,
            0xA8,  # multiplex ratio
            0x3F,  # duty = 1/64
            0xD3,  # set display offset
            0x00,  # no shift
            0x40,  # Set Display Start Line
            0x8d,  # set charge pump enable
            0x14,
            0x20,
            0x02,
            #0x95,
            0xa0,
            0xc8,
            0xDA,  # set COM pins
            0x12,
            0xAD,  # Internal IREF Setting
            0x30,
            0x81,  # contract control
            0xFF,  # 128
            0xD9,  # set pre-charge period
            0x22,
            0xDB,  # set vcomh
            0x20,
            0xA4,  # Set Entire Display On/Off
            0xA6,  # normal / reverse
            #0x0C,  # set lower column address
            #0x11,  # set higher column address
            0xAF   # display ON
        ]
        for cmd in hex_values:
            self.write_cmd(cmd)
        self.fill(0)
        self.show()
    def poweroff(self):
        self.write_cmd(SET_DISP)
    def poweron(self):
        self.write_cmd(SET_DISP | 0x01)
    def contrast(self, contrast):
        self.write_cmd(SET_CONTRAST)
        self.write_cmd(contrast)
    def invert(self, invert):
        self.write_cmd(SET_NORM_INV | (invert & 1))
    def rotate(self, rotate):
        self.write_cmd(SET_COM_OUT_DIR | ((rotate & 1) << 3))
        self.write_cmd(SET_SEG_REMAP | (rotate & 1))
    def show(self):
        #self.write_cmd(SET_COL_ADDR)
        #self.write_cmd(x0)
        #self.write_cmd(x1)
        #self.write_cmd(SET_PAGE_ADDR)
        #self.write_cmd(0)
        #self.write_cmd(self.pages - 1)
        #self.write_data(self.buffer)
       
        for row in range(8):
            self.set_cursor(0, row)
            for col in range(128):
                self.write_data(self.buffer[(128*row+col)])
   
    def set_cursor(self, x, y):
        #self.write_cmd(0xb0+y)
        self.write_cmd(0xb0+y)
        self.write_cmd(((x+self.x_offset)&0xf0) >> 4 | 0x10)
        self.write_cmd((x+self.x_offset)&0x0f)
class SSD1306_I2C(SSD1306):
    def __init__(self, i2c, width=128, height=64, addr=0x3C, external_vcc=False):
        self.i2c = i2c
        self.addr = addr
        self.temp = bytearray(2)
        self.write_list = [b"\x40", None]  # Co=0, D/C#=1
        super().__init__(width, height, external_vcc)
    def write_cmd(self, cmd):
        self.temp[0] = 0x00  # Co=1, D/C#=0
        self.temp[1] = cmd
        self.i2c.writeto(self.addr, self.temp)
    def write_bufdata(self, buf):
        self.write_list[1] = buf
        self.i2c.writevto(self.addr, self.write_list)
       
    def write_data(self, data):
        self.temp[0] = 0x40
        self.temp[1] = data
        self.i2c.writeto(self.addr, self.temp)
if __name__ == '__main__':
    from machine import I2C
    i2c = SoftI2C(scl=6, sda=5)   #SoftI2C初始化：scl--> 5, sda --> 4  
    oled = SSD1306_I2C(i2c) # 72 * 40
    oled.fill(0)
    oled.text('hello,abc', 0, 0)
    oled.text('world,def', 0, 8)
    oled.text('micro,ghi', 0, 16)
    oled.text('python,jk', 0, 24)
    oled.text('test,lmnop', 0, 32)
    oled.show()