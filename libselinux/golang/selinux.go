package selinux

/*
 The selinux package is a go bindings to libselinux required to add selinux
 support to docker.

 Author Dan Walsh <dwalsh@redhat.com>

 Used some ideas/code from the go-ini packages https://github.com/vaughan0
 By Vaughan Newton
*/

// #cgo pkg-config: libselinux
// #include <selinux/selinux.h>
// #include <stdlib.h>
import "C"
import (
	"encoding/binary"
	"crypto/rand"
	"unsafe"
	"fmt"
	"bufio"
	"regexp"
	"io"
	"os"
	"strings"
)

var (
	assignRegex  = regexp.MustCompile(`^([^=]+)=(.*)$`)
	mcs_list = make(map[string]bool)
)

func Matchpathcon(path string, mode int) (string, error) {
	var con C.security_context_t
	var scon string
	rc, err := C.matchpathcon(C.CString(path),C.mode_t(mode), &con)
	if rc == 0 {
		scon = C.GoString(con)
		C.free(unsafe.Pointer(con))
	}
	return scon, err
}

func Setfilecon(path,scon string) (int, error) {
        rc, err := C.lsetfilecon(C.CString(path),C.CString(scon))
	return int(rc), err
}

func Setexeccon(scon string) (int, error) {
	var val *C.char
	if ! Selinux_enabled() {
		return 0, nil
	}
	if scon != "" {
		val = C.CString(scon)
	} else {
		val = nil
	}
        rc, err := C.setexeccon(val)
	return int(rc), err
}

type Context struct {
	con []string
}
func (c *Context) Set_user(user string) {
	c.con[0]=user
}
func (c *Context) Get_user() string {
	return c.con[0]
}
func (c *Context) Set_role(role string) {
	c.con[1]=role
}
func (c *Context) Get_role() string {
	return c.con[1]
}
func (c *Context) Set_type(setype string) {
	c.con[2]=setype
}
func (c *Context) Get_type() string {
	return c.con[2]
}
func (c *Context) Set_level(mls string) {
	c.con[3]=mls
}
func (c *Context) Get_level() string {
	return c.con[3]
}
func (c *Context) Get() string{
	return strings.Join(c.con,":")
}
func (c *Context) Set(scon string) {
	c.con = strings.SplitN(scon,":",4)
}
func New_context(scon string) Context {
	var con Context
	con.Set(scon)
	return con
}

func Is_selinux_enabled() bool {
	b := C.is_selinux_enabled()
	if b > 0 {
		return true;
	}
	return false
}

func Selinux_enabled() bool {
	b := C.is_selinux_enabled()
	if b > 0 {
		return true;
	}
	return false
}

const (
	Enforcing = 1
	Permissive = 0
	Disabled = -1
)

func Selinux_getenforce() int {
	return int(C.security_getenforce())
}

func Selinux_getenforcemode() (int) {
	var enforce C.int
	C.selinux_getenforcemode(&enforce)
	return int(enforce)
}

func mcs_add(mcs string) {
	mcs_list[mcs] = true
}

func mcs_delete(mcs string) {
	mcs_list[mcs] = false
}

func mcs_exists(mcs string) bool {
	return mcs_list[mcs] 
}

func uniq_mcs(catRange uint32) string {
	var n uint32
	var c1,c2 uint32
	var mcs string
	for ;; {
		binary.Read(rand.Reader, binary.LittleEndian, &n)
		c1 = n % catRange
		binary.Read(rand.Reader, binary.LittleEndian, &n)
		c2 = n % catRange
		if c1 == c2 {
			continue
		} else {
			if c1 > c2 {
				t := c1
				c1 = c2
				c2 = t
			}
		}
		mcs = fmt.Sprintf("s0:c%d,c%d", c1, c2)
		if mcs_exists(mcs) {
			continue
		}
		mcs_add(mcs)
		break
	}
	return mcs
}
func free_context(process_label string) {
	var scon Context
	scon = New_context(process_label)
	mcs_delete(scon.Get_level())
}

func Get_lxc_contexts() (process_label string, file_label string) {
	var val, key string
	var bufin *bufio.Reader
	if ! Selinux_enabled() {
		return
	}
	lxc_path := C.GoString(C.selinux_lxc_contexts_path())
	file_label = "system_u:object_r:svirt_sandbox_file_t:s0"
	process_label = "system_u:system_r:svirt_lxc_net_t:s0"

	in, err := os.Open(lxc_path)
	if err != nil {
		goto exit
	}

	defer in.Close()
	bufin = bufio.NewReader(in)

	for done := false; !done; {
		var line string
		if line, err = bufin.ReadString('\n'); err != nil {
			if err == io.EOF {
				done = true
			} else {
				goto exit
			}
		}
		line = strings.TrimSpace(line)
		if len(line) == 0 {
			// Skip blank lines
			continue
		}
		if line[0] == ';' || line[0] == '#' {
			// Skip comments
			continue
		}
		if groups := assignRegex.FindStringSubmatch(line); groups != nil {
			key, val = strings.TrimSpace(groups[1]), strings.TrimSpace(groups[2])
			if key == "process" {
				process_label = strings.Trim(val,"\"")
			}
			if key == "file" {
				file_label = strings.Trim(val,"\"")
			}
		}
	}
exit:
	var scon Context
	mcs := uniq_mcs(1024)
	scon = New_context(process_label)
	scon.Set_level(mcs)
	process_label = scon.Get()
	scon = New_context(file_label)
	scon.Set_level(mcs)
	file_label = scon.Get()
	return process_label, file_label
}

func CopyLevel (src, dest string) (string, error) {
	if ! Selinux_enabled() {
		return "", nil
	}
	if src == "" {
		return "", nil
	}
	rc, err := C.security_check_context(C.CString(src))
	if rc != 0 {
		return "", err
	}
	rc, err = C.security_check_context(C.CString(dest))
	if rc != 0 {
		return "", err
	}
	scon := New_context(src)
	tcon := New_context(dest)
	tcon.Set_level(scon.Get_level())
	return tcon.Get(), nil
}

func Test() {
	var plabel,flabel string
	if ! Selinux_enabled() {
		return
	}

	plabel, flabel = Get_lxc_contexts()
	fmt.Println(plabel)
	fmt.Println(flabel)
	free_context(plabel)
	plabel, flabel = Get_lxc_contexts()
	fmt.Println(plabel)
	fmt.Println(flabel)
	free_context(plabel)
	if Selinux_enabled() {
		fmt.Println("Enabled")
	} else {
		fmt.Println("Disabled")
	}
	fmt.Println(Selinux_getenforce())
	fmt.Println(Selinux_getenforcemode())
	flabel,_ = Matchpathcon("/home/dwalsh/.emacs", 0)
	fmt.Println(flabel)
}
