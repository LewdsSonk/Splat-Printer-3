/*
Nintendo Switch Fightstick - Proof-of-Concept

Based on the LUFA library's Low-Level Joystick Demo
	(C) Dean Camera
Based on the HORI's Pokken Tournament Pro Pad design
	(C) HORI

This project implements a modified version of HORI's Pokken Tournament Pro Pad
USB descriptors to allow for the creation of custom controllers for the
Nintendo Switch. This also works to a limited degree on the PS3.

Since System Update v3.0.0, the Nintendo Switch recognizes the Pokken
Tournament Pro Pad as a Pro Controller. Physical design limitations prevent
the Pokken Controller from functioning at the same level as the Pro
Controller. However, by default most of the descriptors are there, with the
exception of Home and Capture. Descriptor modification allows us to unlock
these buttons for our use.
*/

/** \file
 *
 *  Main source file for the posts printer demo. This file contains the main tasks of
 *  the demo and is responsible for the initial application hardware configuration.
 */

#include "Joystick.h"

extern const uint8_t image_data[0x12c2] PROGMEM;

//Global values for the options
int cautiousoffset = 0; //Could possibly change into a bool and then make the offset somewhere else in the future?
						//X offset adds X * 120 inputs in total, since the image is 320x120.
bool opposite = false;
bool slowmode = false;
bool endsave = false;
bool vertical = false;
void CheckImageOptions(void) {
	for (int current_bit = 0; current_bit < 8; current_bit++){
		if (pgm_read_byte(&(image_data[current_bit/8])) & 1 << (current_bit % 8)){
			switch(current_bit){
				case 0:	cautiousoffset = 3; break;
				case 1: opposite = true; break;
				case 2: slowmode = true; break;
				case 3: endsave = true; break;
				case 4: vertical = true; break;
				case 5: break;
				case 6: break;
				case 7: break;
				default: break;
			}
		}
	}
}

// Main entry point.
int main(void) {
	// We'll start by performing hardware and peripheral setup.
	SetupHardware();
	// We'll then enable global interrupts for our use.
	GlobalInterruptEnable();
	//Lastly, for the image printing, we'll check the options in the first byte of the image.
	CheckImageOptions();
	// Once that's done, we'll enter an infinite loop.
	for (;;)
	{
		// We need to run our task to process and deliver data for our IN and OUT endpoints.
		HID_Task();
		// We also need to run the main USB management task.
		USB_USBTask();
	}
}

// Configures hardware and peripherals, such as the USB peripherals.
void SetupHardware(void) {
	// We need to disable watchdog if enabled by bootloader/fuses.
	MCUSR &= ~(1 << WDRF);
	wdt_disable();

	// We need to disable clock division before initializing the USB hardware.
	clock_prescale_set(clock_div_1);
	// We can then initialize our hardware and peripherals, including the USB stack.

	#ifdef ALERT_WHEN_DONE
	// Both PORTD and PORTB will be used for the optional LED flashing and buzzer.
	#warning LED and Buzzer functionality enabled. All pins on both PORTB and \
PORTD will toggle when printing is done.
	DDRD  = 0xFF; //Teensy uses PORTD
	PORTD =  0x0;
                  //We'll just flash all pins on both ports since the UNO R3
	DDRB  = 0xFF; //uses PORTB. Micro can use either or, but both give us 2 LEDs
	PORTB =  0x0; //The ATmega328P on the UNO will be resetting, so unplug it?
	#endif
	// The USB stack should be initialized last.
	USB_Init();
}

// Fired to indicate that the device is enumerating.
void EVENT_USB_Device_Connect(void) {
	// We can indicate that we're enumerating here (via status LEDs, sound, etc.).
}

// Fired to indicate that the device is no longer connected to a host.
void EVENT_USB_Device_Disconnect(void) {
	// We can indicate that our device is not ready (via status LEDs, sound, etc.).
}

// Fired when the host set the current configuration of the USB device after enumeration.
void EVENT_USB_Device_ConfigurationChanged(void) {
	bool ConfigSuccess = true;

	// We setup the HID report endpoints.
	ConfigSuccess &= Endpoint_ConfigureEndpoint(JOYSTICK_OUT_EPADDR, EP_TYPE_INTERRUPT, JOYSTICK_EPSIZE, 1);
	ConfigSuccess &= Endpoint_ConfigureEndpoint(JOYSTICK_IN_EPADDR, EP_TYPE_INTERRUPT, JOYSTICK_EPSIZE, 1);

	// We can read ConfigSuccess to indicate a success or failure at this point.
}

// Process control requests sent to the device from the USB host.
void EVENT_USB_Device_ControlRequest(void) {
	// We can handle two control requests: a GetReport and a SetReport.

	// Not used here, it looks like we don't receive control request from the Switch.
}

// Process and deliver data from IN and OUT endpoints.
void HID_Task(void) {
	// If the device isn't connected and properly configured, we can't do anything here.
	if (USB_DeviceState != DEVICE_STATE_Configured)
		return;

	// We'll start with the OUT endpoint.
	Endpoint_SelectEndpoint(JOYSTICK_OUT_EPADDR);
	// We'll check to see if we received something on the OUT endpoint.
	if (Endpoint_IsOUTReceived())
	{
		// If we did, and the packet has data, we'll react to it.
		if (Endpoint_IsReadWriteAllowed())
		{
			// We'll create a place to store our data received from the host.
			USB_JoystickReport_Output_t JoystickOutputData;
			// We'll then take in that data, setting it up in our storage.
			while(Endpoint_Read_Stream_LE(&JoystickOutputData, sizeof(JoystickOutputData), NULL) != ENDPOINT_RWSTREAM_NoError);
			// At this point, we can react to this data.

			// However, since we're not doing anything with this data, we abandon it.
		}
		// Regardless of whether we reacted to the data, we acknowledge an OUT packet on this endpoint.
		Endpoint_ClearOUT();
	}

	// We'll then move on to the IN endpoint.
	Endpoint_SelectEndpoint(JOYSTICK_IN_EPADDR);
	// We first check to see if the host is ready to accept data.
	if (Endpoint_IsINReady())
	{
		// We'll create an empty report.
		USB_JoystickReport_Input_t JoystickInputData;
		// We'll then populate this report with what we want to send to the host.
		GetNextReport(&JoystickInputData);
		// Once populated, we can output this data to the host. We do this by first writing the data to the control stream.
		while(Endpoint_Write_Stream_LE(&JoystickInputData, sizeof(JoystickInputData), NULL) != ENDPOINT_RWSTREAM_NoError);
		// We then send an IN packet on this endpoint.
		Endpoint_ClearIN();
	}
}

typedef enum {
	SYNC_CONTROLLER,
	SYNC_POSITION,
	FILL_BLACK,
	FILL_BLACK_YSHIFT,
	FILL_BLACK_STOP_X,
	FILL_BLACK_STOP_Y,
	STOP_X,
	STOP_Y,
	MOVE_X,
	MOVE_Y,
	VERTICAL_STOP_X,
	VERTICAL_STOP_Y,
	VERTICAL_MOVE_X,
	VERTICAL_MOVE_Y,
	ENDSAVE,
	DONE
} State_t;
State_t state = SYNC_CONTROLLER;

#define ECHOES 2
int echoes = 0;
USB_JoystickReport_Input_t last_report;

#define FLAGS_OFFSET 8
int report_count = 0;
int xpos = 0;
int ypos = 0;
int blackfill = 0;
int portsval = 0;
bool slowflip = false;
bool inkstopper = true;

// Prepare the next report for the host.
void GetNextReport(USB_JoystickReport_Input_t* const ReportData) {

	if (slowmode == true && inkstopper == false){
		if (slowflip == false)
			slowflip = true;
		else
			slowflip = false;
	}

	// Prepare an empty report
	memset(ReportData, 0, sizeof(USB_JoystickReport_Input_t));
	ReportData->LX = STICK_CENTER;
	ReportData->LY = STICK_CENTER;
	ReportData->RX = STICK_CENTER;
	ReportData->RY = STICK_CENTER;
	ReportData->HAT = HAT_CENTER;

	// Repeat ECHOES times the last report
	if (echoes > 0)
	{
		memcpy(ReportData, &last_report, sizeof(USB_JoystickReport_Input_t));
		echoes--;
		return;
	}

	// States and moves management
	if (slowflip == false || slowmode == false){
		switch (state)
		{
			case SYNC_CONTROLLER:
				if (report_count > 100)
				{
					report_count = 0;
					state = SYNC_POSITION;
				}
				else if (report_count == 25 || report_count == 50)
				{
					ReportData->Button |= SWITCH_L | SWITCH_R;
				}
				else if (report_count == 75 || report_count == 100)
				{
					ReportData->Button |= SWITCH_A;
				}
				report_count++;
				break;
			case SYNC_POSITION:
				if (report_count >= 250)
				{
					report_count = 0;
					xpos = 0;
					ypos = 0;
					if (opposite == false){
						inkstopper = false;
						state = STOP_X;
					}
					else
						state = FILL_BLACK_STOP_X;
				}
				else
				{
					// Moving faster with LX/LY
					ReportData->LX = STICK_MIN;
					ReportData->LY = STICK_MIN;
				}
				if (report_count == 75 || report_count == 150)
				{
					// Clear the screen
					ReportData->Button |= SWITCH_LCLICK;
					// Choose the smaller pencil
					ReportData->Button |= SWITCH_L;
				}
				report_count++;
				break;
			case FILL_BLACK_STOP_X:
				state = FILL_BLACK;
				break;
			case FILL_BLACK_STOP_Y:
				state = FILL_BLACK_YSHIFT;
				break;
			case FILL_BLACK:
				if (report_count <= 100){
					if (report_count % 25 == 0){
						ReportData->Button |= SWITCH_R; //Making sure it picks the larger brush again
						ReportData->HAT = HAT_BOTTOM;
					}
					report_count++;
				}
				else if (report_count > 115 - 1 && report_count < 300){
					if(report_count == 190 || report_count == 265)
						ReportData->Button |= SWITCH_L;
					ReportData->LX = STICK_MIN;
					ReportData->LY = STICK_MIN;
					report_count++;
				}
				else if (report_count >= 300){
					blackfill = 0;
					report_count = 0;
					xpos = 0;
					ypos = 0;
					inkstopper = false;

					if (vertical == false)
						state = STOP_X;
					else
						state = VERTICAL_STOP_Y
				}
				else{
					if (ypos % 2)
					{
						if (xpos < 123)
							ReportData->LX = STICK_MIN;
						xpos--;
					}
					else
					{
						if (xpos > 2)
							ReportData->LX = STICK_MAX;
						xpos++;
					}

					if (xpos > -1 && xpos < 125){ //125 is just an estimated value to make sure it gets to the left/right
						ReportData->Button |= SWITCH_A;
						state = FILL_BLACK_STOP_X;
					}
					else{
						if (ypos % 2)
							xpos = 0;
						else
							xpos = 125 - 1;
						ypos += 1;
						state = FILL_BLACK_STOP_Y;
					}
				}
				break;
			case FILL_BLACK_YSHIFT: //has to happen 14 times; 115 = 14 + 101 initial steps
				if (report_count >= 115 - 1){
					report_count++;
					state = FILL_BLACK_STOP_X;
				}
				if (blackfill < 9){
					ReportData->HAT = HAT_BOTTOM;
					state = FILL_BLACK_STOP_Y;
					blackfill++;
				}
				else{
					blackfill = 0;
					report_count++;
					state = FILL_BLACK_STOP_X;
				}
				break;

			case STOP_X:
				state = MOVE_X;
				break;
			case STOP_Y:
				if (ypos < 120 - 1)
					state = MOVE_Y;
				else
					if (endsave == true)
						state = ENDSAVE;
					else
						state = DONE;
				break;
			case MOVE_X:
				if (ypos % 2)
				{
					ReportData->HAT = HAT_LEFT;
					xpos--;
				}
				else
				{
					ReportData->HAT = HAT_RIGHT;
					xpos++;
				}
				if (xpos > 0 - cautiousoffset && xpos < 320 - 1 + cautiousoffset)
					state = STOP_X;
				else{
					if (ypos % 2)
						xpos = 0;
					else
						xpos = 320 - 1;
					state = STOP_Y;
				}
				break;
			case MOVE_Y:
				ReportData->HAT = HAT_BOTTOM;
				ypos++;
				state = STOP_X;
				break;

			case VERTICAL_STOP_Y:
				state = MOVE_Y
				break;
			case VERTICAL_STOP_X:
				if (xpos < 320 - 1)
					state = MOVE_X;
				else
					if (endsave == true)
						state = ENDSAVE;
					else
						state = DONE;
				break;
			case VERTICAL_MOVE_Y:
				if (xpos % 2)
				{
					ReportData->HAT = HAT_BOTTOM;
					ypos--;
				}
				else
				{
					ReportData->HAT = HAT_TOP;
					ypos++;
				}
				if (ypos > 0 - cautiousoffset && ypos < 120 - 1 + cautiousoffset)
					state = STOP_Y;
				else{
					if (xpos % 2)
						ypos = 0;
					else
						ypos = 120 - 1;
					state = STOP_X;
				}
				break;
			case VERTICAL_MOVE_X:
				ReportData->HAT = HAT_RIGHT;
				xpos++;
				state = STOP_Y;
				break;
			case ENDSAVE:
				if (report_count <= 100){
					if (report_count == 50)
						ReportData->Button |= SWITCH_MINUS;
				}
				else {
					state = DONE;
				}
				report_count++;
				break;
			case DONE:
				#ifdef ALERT_WHEN_DONE
				portsval = ~portsval;
				PORTD = portsval; //flash LED(s) and sound buzzer if attached
				PORTB = portsval;
				_delay_ms(250);
				#endif
				return;
		}
	}

	// Inking; It should be already mapped so it will ink according to where in the image it is, correctly.
	if (slowflip == true || slowmode == false){
		if (inkstopper == false && xpos >= 0 && xpos < 320){
			if (opposite == false){
				if (pgm_read_byte(&(image_data[(xpos / 8) + (ypos * 40) + FLAGS_OFFSET/8])) & 1 << (xpos % 8))
					ReportData->Button |= SWITCH_A;
			}
			else{
				if (!(pgm_read_byte(&(image_data[(xpos / 8) + (ypos * 40) + FLAGS_OFFSET/8])) & 1 << (xpos % 8)))
					ReportData->Button |= SWITCH_B;
			}
		}
	}

	// Prepare to echo this report
	memcpy(&last_report, ReportData, sizeof(USB_JoystickReport_Input_t));
	echoes = ECHOES;
}