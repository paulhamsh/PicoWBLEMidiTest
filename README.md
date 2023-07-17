# PicoWBLEMidiTest
Basic BLE Midi test for Pico W in Micropython

Requires two Pico Ws - one peripheral, one central. 

Both need ble_advertising.py.
Peripheral needs main.py
Central needsd ble_midi_central.py

main.py will send midi BLE messages one a second
ble_midi_central.py will scan for the other Pico W, connect and get notifications on each message

Proves it works!

Interesting things I may forget later on:
1. Micropython notifies without even checking the CCCD (0x2902)
2. Micropython has no subscribe function - you have to gattc write to 0x2902 to register for notifiations
3. Unless the device you are connecting to is a Micropython device - see point (1)
4. Micropython allows access to the full advertisement data payload - wooeee
5. And to the scan data payload (type 4)


And a trace of the NimBLE-Arduino and Nimble CCCD processing    


```
Example Nimble descriptors
--------------------------
https://github.com/espressif/esp-idf/tree/master/examples/bluetooth/nimble/bleprph/main/

// Example descriptors added as services

gatt_svr.c:		static const struct ble_gatt_svc_def gatt_svr_svcs[] = {
   			  {
        		    	  /*** Service: Security test. */
        		    	  .type = BLE_GATT_SVC_TYPE_PRIMARY,
        		   	  .uuid = &gatt_svr_svc_sec_test_uuid.u,
        		   	  .characteristics = (struct ble_gatt_chr_def[]) { {
        		      	      /*** Characteristic: Random number generator. */
            		      .uuid = &gatt_svr_chr_sec_test_rand_uuid.u,
            		      .access_cb = gatt_svr_chr_access_sec_test,
            		      .flags = BLE_GATT_CHR_F_READ | BLE_GATT_CHR_F_READ_ENC,
        		   	      }, {
            		      /*** Characteristic: Static value. */
            		      .uuid = &gatt_svr_chr_sec_test_static_uuid.u,
            		      .access_cb = gatt_svr_chr_access_sec_test,
            		      .flags = BLE_GATT_CHR_F_READ |
                  	               BLE_GATT_CHR_F_WRITE | BLE_GATT_CHR_F_WRITE_ENC,
        		              }, {
            		      0, /* No more characteristics in this service. */
        		            } },
                           },
                           {
        		            0, /* No more services. */
                           },
                        	};

			ble_gatts_add_svcs(gatt_svr_svcs)


Create CCCD
-----------
https://github.com/espressif/esp-nimble/tree/master/nimble/host/src

// Create and register the descriptors

ble_gatts.c:		ble_gatts_start():
				...
				rc = ble_att_svr_start()
				...
				for (i = 0; i < ble_gatts_num_svc_defs; i++) {
        			  	  rc = ble_gatts_register_svcs(ble_gatts_svc_defs[i],
                                                                ble_hs_cfg.gatts_register_cb,
                                                                ble_hs_cfg.gatts_register_arg);
				  ...
				}


			ble_gatts_register_svcs():
				while (total_registered < num_svcs) {
        			  	  rc = ble_gatts_register_round(&cur_registered, cb, cb_arg);
 				  ...
        			  	  total_registered += cur_registered;
    				}

			ble_gatts_register_round():
				for (i = 0; i < ble_gatts_num_svc_entries; i++) {
        			  	  entry = ble_gatts_svc_entries + i;

        			  	  if (entry->handle == 0) {
            			    rc = ble_gatts_register_svc(entry->svc, &handle, cb, cb_arg);
				    ....
				  }
				}


			ble_gatts_register_svc():
				/* Register service definition attribute */
				rc = ble_att_svr_register(uuid, BLE_ATT_F_READ, 0, out_handle,
                                                           ble_gatts_svc_access, (void *)svc);

				/* Register each include. */
   				if (svc->includes != NULL) {
        			  	  for (i = 0; svc->includes[i] != NULL; i++) {
            			    ...
           			    rc = ble_gatts_register_inc(ble_gatts_svc_entries + idx);
          			    ...
        			  	  }
    				}

				/* Register each characteristic. */
				if (svc->characteristics != NULL) {
      				  for (chr = svc->characteristics; chr->uuid != NULL; chr++) {
            			    rc = ble_gatts_register_chr(svc, chr, register_cb, cb_arg);
				    ...
			          }
     				}
			

			ble_gatts_register_chr():
				/* Register characteristic definition attribute */
    				rc = ble_att_svr_register(...)

				/* Register characteristic value attribute */
				rc = ble_att_svr_register(...)

				if (ble_gatts_chr_clt_cfg_allowed(chr) != 0) {
			          rc = ble_gatts_register_clt_cfg_dsc(&dsc_handle);
				  ...
				}

				/* Register each descriptor. */
				if (chr->descriptors != NULL) {
				  for (dsc = chr->descriptors; dsc->uuid != NULL; dsc++) {
				    rc = ble_gatts_register_dsc(svc, chr, dsc, def_handle, 
register_cb, cb_arg);
				    ....
				  }
				}
			// Create the CCCD with callback of ble_gatts_clt_cfg_access
			ble_gatts_register_clt_cfg_dsc():
				rc = ble_att_svr_register(uuid_ccc, BLE_ATT_F_READ | BLE_ATT_F_WRITE,
 0,  att_handle, ble_gatts_clt_cfg_access,
 NULL);

			ble_gatts_register_dsc():
				rc = ble_att_svr_register(dsc->uuid, dsc->att_flags, 
 dsc->min_key_size, &dsc_handle,
 ble_gatts_dsc_access, (void *)dsc);

// Register a host attribute with the BLE stack.
			ble_att_svr_register():
				...



Start the service
-----------------

>> https://github.com/espressif/esp-idf/tree/master/examples/bluetooth/nimble/bleprph/main/

main.c:			app_main():
                        		nimble_port_init()

>> https://github.com/espressif/esp-nimble/tree/master/porting/nimble/src

nimble_port.c:		nimbe_port_init():
				esp_nimble_init()

			esp_nimble_init():
				ble_transport_hs_init()


>> https://github.com/espressif/esp-nimble/tree/master/nimble/host/src

ble_hs.c:		ble_transport_hs_init():
                                …
                                ble_hs_init()
                                …

                		ble_hs_init():
                                …
ble_npl_event_init(&ble_hs_ev_start_stage1, 
  ble_hs_event_start_stage1, NULL);
                			ble_npl_event_init(&ble_hs_ev_start_stage2, 
  ble_hs_event_start_stage2, NULL
…

			ble_hs_event_start_stage2():
               			
                			ble_hs_start()
                			…

			ble_hs_start():
               			…
                			ble_gatts_start()
                			…

			ble_gatts.c:
                			ble_gatts_start():



>> https://github.com/h2zero/NimBLE-Arduino/tree/master/src

// In Arduino NimBLE server start is like this:

NimBLEServer.cpp:	NimBLEServer::start():
				…
			  	rc = ble_gatts_start();
				…


	
Write on CCCD from client
-------------------------
>> https://github.com/espressif/esp-nimble/tree/master/nimble/host/src
// Turn write to CCCD into a BLE EVENT - BLE_GAP_EVENT_SUBSCRIBE
// Receive the CCCD access
ble_gatts.c:		ble_gatts_clt_cfg_access():
				ble_gatts_subscribe_event(...BLE_GAP_SUBSCRIBE_REASON_WRITE...)

// Create a gatt event
ble_gatts.c: 		ble_gatts_subscribe_event():
				ble_gap_subscribe_event(...)

// Create a gap event
ble_gap.c:		ble_gap_subscribe_event():
				event.type = BLE_GAP_EVENT_SUBSCRIBE
				ble_gap_event_listener_call(&event);
    				ble_gap_call_conn_event_cb(&event, conn_handle);


>> https://github.com/h2zero/NimBLE-Arduino/tree/master/src

// Handle the event
NimBLEServer.cpp:	NimBLEServer::handleGapEvent():
				case BLE_GAP_EVENT_SUBSCRIBE:
				  for(auto &it : server->m_notifyChrVec) {
       			            if(it->getHandle() == event->subscribe.attr_handle) {
				      …
				      // break if not the one we want
				      …
				      it->setSubscribe(event);
				    }
				  }

// Set subscribe status in m_subscribedVec
NimBLECharacteristic.h:	
			// in class definition
			std::vector<std::pair<uint16_t, uint16_t>>  m_subscribedVec;

NimBLECharacteristic.cpp:	
			NimBLECharacteristic::setSubscribe()



/////////////////
To check: BLE_GAP_EVENT_NOTIFY_TX

```
