#!/bin/bash

SCRIPT_DIR="$( cd -- "$( dirname -- "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )"

function get-data {

    # Check if there is internet connectivity
    wget -q --spider http://google.com &> /dev/null
    if [ $? -eq 0 ]; then

        # Download new exchange rate database
        wget -q -O /tmp/eurofxref-hist.zip.tmp https://www.ecb.europa.eu/stats/eurofxref/eurofxref-hist.zip &> /dev/null
        mv /tmp/eurofxref-hist.zip.tmp $SCRIPT_DIR/eurofxref-hist.zip

    fi
    
}

# Check if database exists
if [ ! -f "$SCRIPT_DIR/eurofxref-hist.zip" ]; then
    get-data
fi

# Check if there is a more recent version available than the currently active database
currentVersion=$(ls -al --time-style=long-iso $SCRIPT_DIR/eurofxref-hist.zip | awk '{print $6}')
if [ "$currentVersion" != "$(date -u '+%Y-%m-%d')" ]; then

    # Count how many days have passed since current active version
    days_since_update=$(( ($(date +%s) - $(date --date="$currentVersion" +%s) )/(60*60*24) ))

    for i in $(seq 0 $days_since_update); do

        currentVersion=$(ls -al --time-style=long-iso $SCRIPT_DIR/eurofxref-hist.zip | awk '{print $6}')
        checkDate=$(date --date="$i days ago" +"%u")

        # Should not be a weekend
        if [[ "$checkDate" != @("6"|"7") ]]; then

            # Should not be a holiday
            fixedHoliday=$(grep "Fixed holidays" $SCRIPT_DIR/update_data.sh | grep -o $(date --date="$i days ago" '+%m-%d'))
            moveableHoliday=$(tail -n 6 $SCRIPT_DIR/update_data.sh | grep -o $(date --date="$i days ago" '+%y-%m-%d'))

            if [ ! $fixedHoliday ] || [ ! $moveableHoliday ]; then

                # Last available database date should not be equal to the current database version date
                checkDate=$(date --date="$i days ago" +"%Y-%m-%d")
                if [ "$checkDate" != "$currentVersion" ]; then

                    if [ $i = 0 ]; then

                        # Exchange rates are not updated by ECB before 16:00 CET (15 UTC without DST)
                        # After 15 UTC the database should most certainly be updated and ready
                        if (( "$(date -u '+%H')" < "15" )); then
                            break
                        else
                            get-data
                            break
                        fi

                    else
                        get-data
                    fi

                fi
            fi
        fi
    done
fi

##
## Holidays
##
## Source: 
## https://www.ecb.europa.eu/services/contacts/working-hours/html/index.en.html 
## https://www.timeanddate.com/holidays/germany/
## 
## Fixed holidays: "01-01", "05-01", "05-09", "10-03", "11-01", "12-24", "12-25", "12-26", "12-31"
##
## Moveable holidays:
## - Good Friday: "22-04-15","23-04-07","24-03-29","25-04-18","26-04-03","27-03-26","28-04-14","29-03-30","30-04-19","31-04-11","32-03-26","33-04-15","34-04-07","35-03-23","36-04-11","37-04-03","38-04-23","39-04-08","40-03-30",
## - Easter Monday:" 22-04-18","23-04-10","24-04-01","25-04-21","26-04-06","27-03-29","28-04-17","29-04-02","30-04-22","31-04-14","32-03-29","33-04-18","34-04-10","35-03-26","36-04-14","37-04-06","38-04-26","39-04-11","40-04-02"
## - Ascension Day: "22-05-26","23-05-18","24-05-09","25-05-29","26-05-14","27-05-06","28-05-25","29-05-10","30-05-30","31-05-22","32-05-06","33-05-26","34-05-18","35-05-03","36-05-22","37-05-14","38-06-03","39-05-19","40-05-10"
## - Whit Monday: "22-06-06","23-05-29","24-05-20","25-06-09","26-05-25","27-05-17","28-06-05","29-05-21","30-06-10","31-06-02","32-05-17","33-06-06","34-05-29","35-05-14","36-06-02","37-05-25","38-06-14","39-05-30","40-05-21"
## - Corpus Christi: "22-06-16","23-06-08","24-05-30","25-06-19","26-06-04","27-05-27","28-06-15","29-05-31","30-06-20","31-06-12","32-05-27","33-06-16","34-06-08","35-05-24","36-06-12","37-06-04","38-06-24","39-06-09","40-05-31"