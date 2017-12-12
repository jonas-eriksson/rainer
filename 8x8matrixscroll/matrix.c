#include <signal.h>
#include <errno.h>
#include <stdio.h>
#include <stdlib.h>
#include "i2c-dev.h"
#include <fcntl.h>
#include "8x8font.h"
#include <string.h>
#include "expr.h"

__u16 block[I2C_SMBUS_BLOCK_MAX];
//global variables used for matrix
int res, i2cbus, daddress, eyeMode, address, size, file;
	unsigned short int   displayBuffer[8];


//Reverse the bits
unsigned  char  reverseBits(unsigned  char num)
{
    unsigned  char count = sizeof(num) * 8 - 1;
    unsigned  char reverse_num = num;
    num >>= 1;
    while(num)
    {
       reverse_num <<= 1;
       reverse_num |= num & 1;
       num >>= 1;
       count--;
    }
    reverse_num <<= count;
    return reverse_num;
}

/* Print n as a binary number */
void printbitssimple(char n) {
        unsigned char i;
        i = 1<<(sizeof(n) * 8 - 1);

        while (i > 0) {
                if (n & i)
                        printf("#");
                else
                        printf(".");
                i >>= 1;
        	}
        printf("\n");
	}


int displayImage(__u16 bmp[], int res, int daddress, int file)
{
        int i;
        for(i=0; i<8; i++)
        {
             block[i] = (bmp[i]&0xfe) >>1 |
             (bmp[i]&0x01) << 7;
        }
        res = i2c_smbus_write_i2c_block_data(file, daddress, 16,
                (__u8 *)block);
        usleep(70000);
}

void  INThandler(int sig)
{
       // Closing file and turning off Matrix

	unsigned short int clear[] = {0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00};

	displayImage(clear,res, daddress, file);

        printf("Closing file and turning off the LED Matrix\n");
        daddress = 0x20;
        for(daddress = 0xef; daddress >= 0xe0; daddress--) {
                res = i2c_smbus_write_byte(file, daddress);
        }

	signal(sig, SIG_IGN);

        close(file);
        exit(0);
}



void genImg(char bmp[]) {
	int Vposition;

	for(Vposition = 0; Vposition < 8 ; Vposition++){
	    displayBuffer[Vposition] = bmp[Vposition];
	}
}


int main(int argc, char *argv[])
{
        //Exit if not enough parameters are added with the executable
        if(argc != 4 ) {
                fprintf(stderr, "Usage:  %s <i2c-bus> <i2c-address> <eyeMode> \n", argv[0]);
                exit(1);
        }


        char *end;
        int count,cont;
        char filename[20];
        unsigned char letter;
        int i,t,y;

        i2cbus   = atoi(argv[1]);
        address  = atoi(argv[2]);
        eyeMode = atoi(argv[3]);
        daddress = 0;
	//char text[strlen(argv[3])+4];



	signal(SIGINT, INThandler);



	//Startup the matrix
	size = I2C_SMBUS_BYTE;
	sprintf(filename, "/dev/i2c-%d", i2cbus);
	file = open(filename, O_RDWR);
	if (file<0) {
		if (errno == ENOENT) {
			fprintf(stderr, "Error: Could not open file "
				"/dev/i2c-%d: %s\n", i2cbus, strerror(ENOENT));
			}
		 else {
			fprintf(stderr, "Error: Could not open file "

				"`%s': %s\n", filename, strerror(errno));
			if (errno == EACCES)
				fprintf(stderr, "Run as root?\n");
		}
		exit(1);
	}

	if (ioctl(file, I2C_SLAVE, address) < 0) {
		fprintf(stderr,
			"Error: Could not set address to 0x%02x: %s\n",
			address, strerror(errno));
		return -errno;
	}


	res = i2c_smbus_write_byte(file, daddress);
	if (res < 0) {
		fprintf(stderr, "Warning - write failed, filename=%s, daddress=%d\n",
			filename, daddress);
	}



	daddress = 0x21; // Start oscillator (page 10)
	//printf("writing: 0x%02x\n", daddress);
	res = i2c_smbus_write_byte(file, daddress);

	daddress = 0x81; // Display on, blinking off (page 11)
	//printf("writing: 0x%02x\n", daddress);
	res = i2c_smbus_write_byte(file, daddress);

	daddress = 0xE1; // Full brightness (page 15) (ADDRESS = 0xe0, brightness = 0x00>>0x0F)
	//printf("Brightness writing: 0x%02x\n", daddress);
	res = i2c_smbus_write_byte(file, daddress);

	daddress = 0x00; // Start writing to address 0 (page 13)
	//printf("Start writing to address 0 writing: 0x%02x\n", daddress);
	res = i2c_smbus_write_byte(file, daddress);


	//Setup the text  argument that was passed to main. remove null and add some extra spaces.
/*
        for(i = 0; i < (strlen(argv[3])) ; i++){
	        text[i] = argv[3][i];
        }
        for(i = 0; i < 4 ; i++){
                text[strlen(argv[3])+i] = 32;
        }
*/






        //put all the characters of the scrolling text in a contiguous block

/*
	int Vposition;
	unsigned short int   displayBuffer[8];
	for(Vposition = 0; Vposition < 8 ; Vposition++){
	    displayBuffer[Vposition] = eye_open_bmp[Vposition];
	}
	*/

unsigned long long brate = 5000;
unsigned long long anim_dly = 7000;


/*
while(1) {
    displayImage(display,res, daddress, file);
}
*/
	//Text scrolling happens here
	//while (1){


switch (eyeMode) {

	case 0: 
        genImg(eye_sleep_bmp);
        displayImage(displayBuffer,res, daddress, file);
        break;

    case 1: 
        genImg(eye_open_bmp);
        displayImage(displayBuffer,res, daddress, file);
        usleep(3000000);
      
        genImg(eye_left_bmp);
        displayImage(displayBuffer,res, daddress, file);
        usleep(1000000);

        genImg(eye_right_bmp);
        displayImage(displayBuffer,res, daddress, file);
        usleep(1000000);

        genImg(eye_open_bmp);
        displayImage(displayBuffer,res, daddress, file);
        usleep(1000000);

        genImg(eye_sleep_bmp);
        displayImage(displayBuffer,res, daddress, file);
        usleep(brate);

        genImg(eye_open_bmp);
        displayImage(displayBuffer,res, daddress, file);
        //usleep(1000000);
        break;

    case 2: 
        genImg(eye_open_bmp);
        displayImage(displayBuffer,res, daddress, file);
        break;

    case 3: 
        genImg(eye_left_bmp);
        displayImage(displayBuffer,res, daddress, file);
        break;
    case 4: 
        genImg(eye_right_bmp);
        displayImage(displayBuffer,res, daddress, file);
        break;

    case 5: 
        genImg(eye_sleep_bmp);
        displayImage(displayBuffer,res, daddress, file);
        usleep(brate);
        genImg(eye_open_bmp);
        displayImage(displayBuffer,res, daddress, file);
        break;

    case 6: 
        genImg(eye_open_bmp);
        displayImage(displayBuffer,res, daddress, file);
        usleep(anim_dly);
        genImg(eye_close1_bmp);
        displayImage(displayBuffer,res, daddress, file);
        usleep(anim_dly);
        genImg(eye_close2_bmp);
        displayImage(displayBuffer,res, daddress, file);
        usleep(anim_dly);
        genImg(eye_close3_bmp);
        displayImage(displayBuffer,res, daddress, file);
        usleep(anim_dly);
        genImg(eye_sleep_bmp);
        displayImage(displayBuffer,res, daddress, file);
        usleep(anim_dly);
        break;


    case 7: 
        genImg(eye_sleep_bmp);
        displayImage(displayBuffer,res, daddress, file);
        usleep(anim_dly);
        genImg(eye_close3_bmp);
        displayImage(displayBuffer,res, daddress, file);
        usleep(anim_dly);
        genImg(eye_close2_bmp);
        displayImage(displayBuffer,res, daddress, file);
        usleep(anim_dly);
        genImg(eye_close1_bmp);
        displayImage(displayBuffer,res, daddress, file);
        usleep(anim_dly);
        genImg(eye_open_bmp);
        displayImage(displayBuffer,res, daddress, file);
        usleep(anim_dly);
        break;


    case 8: 
        genImg(empty_bmp);
        displayImage(displayBuffer,res, daddress, file);
        break;

    case 9: 
        genImg(heart);
        displayImage(displayBuffer,res, daddress, file);
        break;

    case 10: 
        genImg(eye_ur_bmp);
        displayImage(displayBuffer,res, daddress, file);
        break;

    case 11: 
        genImg(eye_ul_bmp);
        displayImage(displayBuffer,res, daddress, file);
        break;

    case 12: 
        genImg(eye_dr_bmp);
        displayImage(displayBuffer,res, daddress, file);
        break;

    case 13: 
        genImg(eye_dl_bmp);
        displayImage(displayBuffer,res, daddress, file);
        break;

    case 14: 
        genImg(eye_open_bmp);
        displayImage(displayBuffer,res, daddress, file);
        //usleep(anim_dly);

        genImg(eye_left_bmp);
        displayImage(displayBuffer,res, daddress, file);
        //usleep(anim_dly);
        
        //genImg(eye_ll_bmp);
        //displayImage(displayBuffer,res, daddress, file);
        //usleep(anim_dly);
        
        genImg(eye_ul_bmp);
        displayImage(displayBuffer,res, daddress, file);
        //usleep(anim_dly);

        
        genImg(eye_up_bmp);
        displayImage(displayBuffer,res, daddress, file);
        //usleep(anim_dly);
        
        genImg(eye_ur_bmp);
        displayImage(displayBuffer,res, daddress, file);
        //usleep(anim_dly);
        
        genImg(eye_right_bmp);
        displayImage(displayBuffer,res, daddress, file);
        //usleep(anim_dly);
        
        genImg(eye_dr_bmp);
        displayImage(displayBuffer,res, daddress, file);
        //usleep(anim_dly);
        
        genImg(eye_down_bmp);
        displayImage(displayBuffer,res, daddress, file);
        //usleep(anim_dly);
        
        genImg(eye_dl_bmp);
        displayImage(displayBuffer,res, daddress, file);
        //usleep(anim_dly);
        
        genImg(eye_left_bmp);
        displayImage(displayBuffer,res, daddress, file);
        //usleep(anim_dly);
        

        genImg(eye_open_bmp);
        displayImage(displayBuffer,res, daddress, file);
        //usleep(anim_dly);
        break;

    case 15: 
        genImg(eye_right_bmp);
        displayImage(displayBuffer,res, daddress, file);
        break;

    case 16: 
        genImg(eye_left_bmp);
        displayImage(displayBuffer,res, daddress, file);
        break;

    case 17: 
        genImg(eye_up_bmp);
        displayImage(displayBuffer,res, daddress, file);
        break;

    case 18: 
        genImg(eye_down_bmp);
        displayImage(displayBuffer,res, daddress, file);
        break;


    case 19: 
        genImg(eye_right_bmp);
        displayImage(displayBuffer,res, daddress, file);
        break;

    case 20: 
        genImg(eye_ll_bmp);
        displayImage(displayBuffer,res, daddress, file);
        break;


    case 21: 
        genImg(eye_uu_bmp);
        displayImage(displayBuffer,res, daddress, file);
        break;

    case 22: 
        genImg(eye_happy_bmp);
        displayImage(displayBuffer,res, daddress, file);
        break;



    case 23: 
        genImg(eye_sleep_bmp);
        displayImage(displayBuffer,res, daddress, file);
        usleep(brate);

        genImg(eye_open_bmp);
        displayImage(displayBuffer,res, daddress, file);
        usleep(1000000);
      
        genImg(eye_left_bmp);
        displayImage(displayBuffer,res, daddress, file);
        usleep(1000000);

        genImg(eye_right_bmp);
        displayImage(displayBuffer,res, daddress, file);
        usleep(1000000);

        genImg(eye_open_bmp);
        displayImage(displayBuffer,res, daddress, file);
        usleep(1000000);

        break;

    case 24: 
        genImg(eye_sleep_bmp);
        displayImage(displayBuffer,res, daddress, file);
        usleep(brate);

        genImg(eye_open_bmp);
        displayImage(displayBuffer,res, daddress, file);
      //  usleep(1000000);
      
        break;


    default:
        genImg(eye_open_bmp);
        displayImage(displayBuffer,res, daddress, file);
        break;
          
}
      
/*
      genImg(mask_blink1);
      displayImage(displayBuffer,res, daddress, file);
      usleep(brate);
      genImg(mask_blink2);
      displayImage(displayBuffer,res, daddress, file);
      usleep(brate);
      genImg(mask_0);
      displayImage(displayBuffer,res, daddress, file);
      usleep(brate);
      genImg(mask_blink2);
      displayImage(displayBuffer,res, daddress, file);
      usleep(brate);
      genImg(mask_blink1);
      displayImage(displayBuffer,res, daddress, file);
      usleep(brate);
      genImg(mask_blink0);
      displayImage(displayBuffer,res, daddress, file);
      usleep(brate);
      genImg(mask_1);
      displayImage(displayBuffer,res, daddress, file);
      usleep(brate);
			    //}
		//}
*/
	//}
 return 0;
}

