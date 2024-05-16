#!/bin/sh

rsync -avh nomad-catalysis_test/ .
rm -rfv nomad-catalysis_test
