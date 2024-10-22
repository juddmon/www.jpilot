#!/bin/bash
echo "Enter 1) Install jpilot 1.8.2"
echo "Enter 2) Install jpilot 2.0.2"
read ANS
#
sudo apt install libusb-0.1-4
sudo dpkg -i ./libpisock9_0.13.0_amd64.deb ./libpisync1_0.13.0_amd64.deb ./pilot-link_0.13.0_amd64.deb
#
case $ANS in
  "1")
    sudo dpkg -i ./jpilot_1.8.2-2_amd64.deb ./jpilot-plugins_1.8.2-2_amd64.deb
    ;;
  "2")
    sudo dpkg -i ./jpilot_2.0.2-1_amd64.deb ./jpilot-plugins_2.0.2-1_amd64.deb
    ;;
  *)
  echo "$ANS: Unknown option."
  exit 1
  ;;
esac
